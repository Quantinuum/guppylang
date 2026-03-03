import ast
import inspect
import linecache
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import FrameType
from typing import ClassVar

from hugr import Wire, ops

from guppylang_internals.ast_util import AstNode, annotate_location
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnexpectedError,
    UnsupportedError,
)
from guppylang_internals.compiler.core import GlobalConstId
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    ParsableDef,
    UnknownSourceError,
)
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomFunctionDef,
    DefaultCallChecker,
)
from guppylang_internals.definition.function import parse_source
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.ipython_inspect import is_running_ipython
from guppylang_internals.span import SourceMap, Span, to_span
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    StructType,
    Type,
)

if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter


@dataclass(frozen=True)
class UncheckedStructField:
    """A single field on a struct whose type has not been checked yet."""

    name: str
    type_ast: ast.expr


@dataclass(frozen=True)
class StructField:
    """A single field on a struct."""

    name: str
    ty: Type


@dataclass(frozen=True)
class RedundantParamsError(Error):
    title: ClassVar[str] = "Generic parameters already specified"
    span_label: ClassVar[str] = "Duplicate specification of generic parameters"
    struct_name: str

    @dataclass(frozen=True)
    class PrevSpec(Note):
        span_label: ClassVar[str] = (
            "Parameters of `{struct_name}` are already specified here"
        )


@dataclass(frozen=True)
class DuplicateFieldError(Error):
    title: ClassVar[str] = "Duplicate field"
    span_label: ClassVar[str] = (
        "Struct `{struct_name}` already contains a field named `{field_name}`"
    )
    struct_name: str
    field_name: str


@dataclass(frozen=True)
class NonGuppyMethodError(Error):
    title: ClassVar[str] = "Not a Guppy method"
    span_label: ClassVar[str] = (
        "Method `{method_name}` of struct `{struct_name}` is not a Guppy function"
    )
    struct_name: str
    method_name: str

    @dataclass(frozen=True)
    class Suggestion(Help):
        message: ClassVar[str] = (
            "Add a `@guppy` annotation to turn `{method_name}` into a Guppy method"
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(NonGuppyMethodError.Suggestion(None))


@dataclass(frozen=True)
class RawStructDef(TypeDef, ParsableDef):
    """A raw struct type definition that has not been parsed yet."""

    python_class: type
    params: None = field(default=None, init=False)  # Params not known yet

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedStructDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        frame = DEF_STORE.frames[self.id]
        cls_def = parse_py_class(self.python_class, frame, sources)
        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        # Look for generic parameters from Python 3.12 style syntax
        params = []
        params_span: Span | None = None
        if sys.version_info >= (3, 12):
            if cls_def.type_params:
                first, last = cls_def.type_params[0], cls_def.type_params[-1]
                params_span = Span(to_span(first).start, to_span(last).end)
                param_vars_mapping: dict[str, Parameter] = {}
                for idx, param_node in enumerate(cls_def.type_params):
                    param = parse_parameter(
                        param_node, idx, globals, param_vars_mapping
                    )
                    param_vars_mapping[param.name] = param
                    params.append(param)

        # The only base we allow is `Generic[...]` to specify generic parameters with
        # the legacy syntax
        match cls_def.bases:
            case []:
                pass
            case [base] if elems := try_parse_generic_base(base):
                # Complain if we already have Python 3.12 generic params
                if params_span is not None:
                    err: Error = RedundantParamsError(base, self.name)
                    err.add_sub_diagnostic(RedundantParamsError.PrevSpec(params_span))
                    raise GuppyError(err)
                params = params_from_ast(elems, globals)
            case bases:
                err = UnsupportedError(bases[0], "Struct inheritance", singular=True)
                raise GuppyError(err)

        fields: list[UncheckedStructField] = []
        used_field_names: set[str] = set()
        used_func_names: dict[str, ast.FunctionDef] = {}
        for i, node in enumerate(cls_def.body):
            match i, node:
                # We allow `pass` statements to define empty structs
                case _, ast.Pass():
                    pass
                # Docstrings are also fine if they occur at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # Ensure that all function definitions are Guppy functions
                case _, ast.FunctionDef(name=name) as node:
                    from guppylang.defs import GuppyDefinition

                    v = getattr(self.python_class, name)
                    if not isinstance(v, GuppyDefinition):
                        raise GuppyError(NonGuppyMethodError(node, self.name, name))
                    used_func_names[name] = node
                    if name in used_field_names:
                        raise GuppyError(DuplicateFieldError(node, self.name, name))
                # Struct fields are declared via annotated assignments without value
                case _, ast.AnnAssign(target=ast.Name(id=field_name)) as node:
                    if node.value:
                        err = UnsupportedError(node.value, "Default struct values")
                        raise GuppyError(err)
                    if field_name in used_field_names:
                        err = DuplicateFieldError(node.target, self.name, field_name)
                        raise GuppyError(err)
                    fields.append(UncheckedStructField(field_name, node.annotation))
                    used_field_names.add(field_name)
                case _, node:
                    err = UnexpectedError(
                        node, "statement", unexpected_in="struct definition"
                    )
                    raise GuppyError(err)

        # Ensure that functions don't override struct fields
        if overridden := used_field_names.intersection(used_func_names.keys()):
            x = overridden.pop()
            raise GuppyError(DuplicateFieldError(used_func_names[x], self.name, x))

        return ParsedStructDef(self.id, self.name, cls_def, params, fields)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw struct definition")


@dataclass(frozen=True)
class ParsedStructDef(TypeDef, CheckableDef):
    """A struct definition whose fields have not been checked yet."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    fields: Sequence[UncheckedStructField]

    def check(self, globals: Globals) -> "CheckedStructDef":
        """Checks that all struct fields have valid types."""
        param_var_mapping = {p.name: p for p in self.params}
        ctx = TypeParsingCtx(globals, param_var_mapping)

        # Before checking the fields, make sure that this definition is not recursive,
        # otherwise the code below would not terminate.
        # TODO: This is not ideal (see todo in `check_instantiate`)
        check_not_recursive(self, ctx)

        fields = [
            StructField(f.name, type_from_ast(f.type_ast, ctx)) for f in self.fields
        ]
        return CheckedStructDef(
            self.id, self.name, self.defined_at, self.params, fields
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        # Obtain a checked version of this struct definition so we can construct a
        # `StructType` instance
        globals = Globals(DEF_STORE.frames[self.id])
        # TODO: This is quite bad: If we have a cyclic definition this will not
        #  terminate, so we have to check for cycles in every call to `check`. The
        #  proper way to deal with this is changing `StructType` such that it only
        #  takes a `DefId` instead of a `CheckedStructDef`. But this will be a bigger
        #  refactor...
        checked_def = self.check(globals)
        return StructType(args, checked_def)


@dataclass(frozen=True)
class CheckedStructDef(TypeDef, CompiledDef):
    """A struct definition that has been fully checked."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    fields: Sequence[StructField]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return StructType(args, self)

    def generated_methods(self) -> list[CustomFunctionDef]:
        """Auto-generated methods for this struct."""

        class ConstructorCompiler(CustomCallCompiler):
            """Compiler for the `__new__` constructor method of a struct."""

            def compile(self, args: list[Wire]) -> list[Wire]:
                return list(self.builder.add(ops.MakeTuple()(*args)))

        constructor_sig = FunctionType(
            inputs=[
                FuncInput(
                    f.ty,
                    InputFlags.Owned if f.ty.linear else InputFlags.NoFlags,
                    f.name,
                )
                for f in self.fields
            ],
            output=StructType(
                defn=self, args=[p.to_bound(i) for i, p in enumerate(self.params)]
            ),
            params=self.params,
        )
        constructor_def = CustomFunctionDef(
            id=DefId.fresh(),
            name="__new__",
            defined_at=self.defined_at,
            ty=constructor_sig,
            call_checker=DefaultCallChecker(),
            call_compiler=ConstructorCompiler(),
            higher_order_value=True,
            higher_order_func_id=GlobalConstId.fresh(f"{self.name}.__new__"),
            has_signature=True,
        )
        return [constructor_def]


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


def try_parse_generic_base(node: ast.expr) -> list[ast.expr] | None:
    """Checks if an AST node corresponds to a `Generic[T1, ..., Tn]` base class.

    Returns the generic parameters or `None` if the AST has a different shape
    """
    match node:
        case ast.Subscript(value=ast.Name(id="Generic"), slice=elem):
            return elem.elts if isinstance(elem, ast.Tuple) else [elem]
        case _:
            return None


@dataclass(frozen=True)
class RepeatedTypeParamError(Error):
    title: ClassVar[str] = "Duplicate type parameter"
    span_label: ClassVar[str] = "Type parameter `{name}` cannot be used multiple times"
    name: str


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


def check_not_recursive(defn: ParsedStructDef, ctx: TypeParsingCtx) -> None:
    """Throws a user error if the given struct definition is recursive."""

    # TODO: The implementation below hijacks the type parsing logic to detect recursive
    #  structs. This is not great since it repeats the work done during checking. We can
    #  get rid of this after resolving the todo in `ParsedStructDef.check_instantiate()`

    def dummy_check_instantiate(
        args: Sequence[Argument],
        loc: AstNode | None = None,
    ) -> Type:
        raise GuppyError(UnsupportedError(loc, "Recursive structs"))

    original = defn.check_instantiate
    object.__setattr__(defn, "check_instantiate", dummy_check_instantiate)
    for fld in defn.fields:
        type_from_ast(fld.type_ast, ctx)
    object.__setattr__(defn, "check_instantiate", original)
