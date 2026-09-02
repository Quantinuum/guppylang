import ast
import inspect
import linecache
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from types import FrameType
from typing import TYPE_CHECKING, ClassVar, TypeGuard

from guppylang_internals.ast_util import AstNode, annotate_location, parse_source
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnsupportedError,
)
from guppylang_internals.definition.common import (
    DefId,
    Definition,
    UnknownSourceError,
)
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.ipython_inspect import is_running_ipython
from guppylang_internals.span import SourceMap, Span, to_span
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.parsing import (
    TypeParsingCtx,
    annotation_nodes,
    parse_parameter,
    try_parse_defn,
)
from guppylang_internals.tys.ty import Type

if TYPE_CHECKING:
    from guppylang_internals.definition.alias import ParsedTypeAliasDef
    from guppylang_internals.definition.enum import ParsedEnumDef
    from guppylang_internals.definition.struct import ParsedStructDef


type ParsedRecursiveTypeDef = "ParsedStructDef | ParsedEnumDef | ParsedTypeAliasDef"


@dataclass(frozen=True)
class RedundantParamsError(Error):
    title: ClassVar[str] = "Generic parameters already specified"
    span_label: ClassVar[str] = "Duplicate specification of generic parameters"
    class_name: str

    @dataclass(frozen=True)
    class PrevSpec(Note):
        span_label: ClassVar[str] = (
            "Parameters of `{class_name}` are already specified here"
        )


@dataclass(frozen=True)
class DuplicateFieldError(Error):
    title: ClassVar[str] = "Duplicate field"
    span_label: ClassVar[str] = (
        "{class_type_capitalized} `{class_name}` already contains a field named "
        "`{field_name}`"
    )
    class_name: str
    field_name: str
    class_type: str

    @property
    def class_type_capitalized(self) -> str:
        return self.class_type.capitalize()


@dataclass(frozen=True)
class NonGuppyMethodError(Error):
    title: ClassVar[str] = "Not a Guppy method"
    span_label: ClassVar[str] = (
        "Method `{method_name}` of {class_type} `{class_name}` is not a Guppy function"
    )
    class_name: str
    method_name: str
    class_type: str
    ann: str

    @dataclass(frozen=True)
    class Suggestion(Help):
        message: ClassVar[str] = (
            "Add a `{ann}` annotation to turn `{method_name}` into a Guppy method"
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(NonGuppyMethodError.Suggestion(None))


@dataclass(frozen=True)
class RepeatedTypeParamError(Error):
    title: ClassVar[str] = "Duplicate type parameter"
    span_label: ClassVar[str] = "Type parameter `{name}` cannot be used multiple times"
    name: str


@dataclass(frozen=True)
class ProtocolHint(Help):
    message: ClassVar[str] = (
        "Add a `@guppy.protocol` annotation to turn this struct into a protocol"
    )


@dataclass(frozen=True)
class UncheckedField:
    """A single field on a struct or enum variant whose type has not been checked yet."""  # noqa: E501

    name: str
    type_ast: ast.expr


@dataclass(frozen=True)
class CheckedField:
    """A single field on a struct or enum variant."""

    name: str
    ty: Type


def check_not_recursive(defn: ParsedRecursiveTypeDef, ctx: TypeParsingCtx) -> None:
    """Raises a user error if a struct, enum, or type alias depends on itself."""
    _check_not_recursive(defn, ctx, [defn.id], set())


def _check_not_recursive(
    defn: ParsedRecursiveTypeDef,
    ctx: TypeParsingCtx,
    path: list[DefId],
    checked: set[DefId],
) -> None:
    for dependency, loc in _dependencies(defn, ctx):
        if dependency.id in path:
            raise GuppyError(UnsupportedError(loc, "Recursive definitions"))
        if dependency.id not in checked:
            dependency_ctx = _type_parsing_ctx(dependency)
            _check_not_recursive(
                dependency, dependency_ctx, [*path, dependency.id], checked
            )

    checked.add(defn.id)


def _dependencies(
    defn: ParsedRecursiveTypeDef, ctx: TypeParsingCtx
) -> Iterator[tuple[ParsedRecursiveTypeDef, AstNode]]:
    for type_ast in _field_type_asts(defn):
        for node in annotation_nodes(type_ast):
            dependency = try_parse_defn(node, ctx)
            if _is_parsed_recursive_type_def(dependency):
                yield dependency, node


def _field_type_asts(defn: ParsedRecursiveTypeDef) -> Iterator[ast.expr]:
    from guppylang_internals.definition.alias import ParsedTypeAliasDef
    from guppylang_internals.definition.enum import ParsedEnumDef
    from guppylang_internals.definition.struct import ParsedStructDef

    if isinstance(defn, ParsedStructDef):
        for field in defn.fields:
            yield field.type_ast
    elif isinstance(defn, ParsedEnumDef):
        for variant in defn.variants.values():
            for field in variant.fields:
                yield field.type_ast
    elif isinstance(defn, ParsedTypeAliasDef):
        yield defn.type_ast
    else:
        raise InternalGuppyError(
            "Expected a parsed struct, enum, or type alias definition"
        )


def _type_parsing_ctx(defn: ParsedRecursiveTypeDef) -> TypeParsingCtx:
    """Returns a type parsing context for the definition's own module scope.

    Recursive checks may walk into definitions imported from other modules, so their
    field annotations must be resolved against the frame where they were defined.
    """
    from guppylang_internals.engine import DEF_STORE

    param_var_mapping = {p.name: p for p in defn.params} if defn.params else {}
    return TypeParsingCtx(Globals(DEF_STORE.frames[defn.id]), param_var_mapping)


def _is_parsed_recursive_type_def(
    defn: Definition | None,
) -> TypeGuard[ParsedRecursiveTypeDef]:
    from guppylang_internals.definition.alias import ParsedTypeAliasDef
    from guppylang_internals.definition.enum import ParsedEnumDef
    from guppylang_internals.definition.struct import ParsedStructDef

    return isinstance(defn, ParsedStructDef | ParsedEnumDef | ParsedTypeAliasDef)


def parse_py_class(
    cls: type, defining_frame: FrameType, sources: SourceMap
) -> ast.ClassDef:
    """Parses a Python class object into an AST."""
    module = inspect.getmodule(cls)
    if module is None:
        raise GuppyError(UnknownSourceError(None, cls))

    # If we are running IPython, `inspect.getsourcefile` won't work if the class was
    # defined inside a cell. See
    #  - https://bugs.python.org/issue33826
    #  - https://github.com/ipython/ipython/issues/11249
    #  - https://github.com/wandb/weave/pull/1864
    if is_running_ipython() and module.__name__ == "__main__":
        file: str | None = defining_frame.f_code.co_filename
    else:
        file = inspect.getsourcefile(cls)
    if file is None:
        raise GuppyError(UnknownSourceError(None, cls))

    # We can't rely on `inspect.getsourcelines` since it doesn't work properly for
    # classes prior to Python 3.13. See https://github.com/quantinuum/guppylang/issues/1107.
    # Instead, we reproduce the behaviour of Python >= 3.13 using the `__firstlineno__`
    # attribute. See https://github.com/python/cpython/blob/3.13/Lib/inspect.py#L1052.
    # In the decorator, we make sure that `__firstlineno__` is set, even if we're not
    # on Python 3.13.
    file_lines = linecache.getlines(file)
    line_offset = cls.__firstlineno__  # type: ignore[attr-defined]
    source_lines = inspect.getblock(file_lines[line_offset - 1 :])
    source, cls_ast, line_offset = parse_source(source_lines, line_offset)

    # Store the source file in our cache
    sources.add_file(file)
    annotate_location(cls_ast, source, file, line_offset)
    if not isinstance(cls_ast, ast.ClassDef):
        raise GuppyError(ExpectedError(cls_ast, "a class definition"))
    return cls_ast


def try_parse_generic_base(node: ast.expr, base_name: str) -> list[ast.expr] | None:
    """Checks if an AST node corresponds to a `base_name[T1, ..., Tn]` base class.

    Returns the generic parameters or `None` if the AST has a different shape
    """
    match node:
        case ast.Subscript(value=ast.Name(id=name), slice=elem) if base_name == name:
            return elem.elts if isinstance(elem, ast.Tuple) else [elem]
        case _:
            return None


def extract_generic_params(
    cls_def: ast.ClassDef, class_name: str, globals: Globals, class_kind: str
) -> list[Parameter]:
    """Extracts generic parameters from a class definition."""
    params: list[Parameter] = []
    params_span: Span | None = None

    # Look for generic parameters from Python 3.12 style syntax
    if cls_def.type_params:
        first, last = cls_def.type_params[0], cls_def.type_params[-1]
        params_span = Span(to_span(first).start, to_span(last).end)
        param_vars_mapping: dict[str, Parameter] = {}
        for idx, param_node in enumerate(cls_def.type_params):
            param = parse_parameter(param_node, idx, globals, param_vars_mapping)
            param_vars_mapping[param.name] = param
            params.append(param)

    base_params: list[Parameter] = []
    for base in cls_def.bases:
        if elems := try_parse_generic_base(base, "Generic"):
            # Complain if there's already been a `Generic[T]` parent
            if base_params != []:
                raise GuppyError(
                    UnsupportedError(
                        base,
                        "Multiple `Generic` inheritance",
                        singular=True,
                    )
                )

            # Complain if we already have Python 3.12 generic params
            if params_span is not None:
                err: Error = RedundantParamsError(base, class_name)
                err.add_sub_diagnostic(RedundantParamsError.PrevSpec(params_span))
                raise GuppyError(err)
            base_params = params_from_ast(elems, globals)
        elif elems := try_parse_generic_base(base, "Protocol"):
            err = UnsupportedError(base, "Protocol base", singular=True)
            err.add_sub_diagnostic(ProtocolHint(None))
            raise GuppyError(err)
        else:
            err = UnsupportedError(
                base,
                f"{class_kind} inheritance",
                singular=True,
            )
            raise GuppyError(err)

    return params + base_params


def params_from_ast(nodes: Sequence[ast.expr], globals: Globals) -> list[Parameter]:
    """Parses a list of AST nodes into unique type parameters.

    Raises user errors if the AST nodes don't correspond to parameters or parameters
    occur multiple times.
    """
    params: list[Parameter] = []
    params_set: set[DefId] = set()
    for node in nodes:
        if isinstance(node, ast.Name) and node.id in globals:
            defn = globals[node.id]
            if isinstance(defn, ParamDef):
                if defn.id in params_set:
                    raise GuppyError(RepeatedTypeParamError(node, node.id))
                params.append(defn.to_param(len(params)))
                params_set.add(defn.id)
                continue
        raise GuppyError(ExpectedError(node, "a type parameter"))
    return params
