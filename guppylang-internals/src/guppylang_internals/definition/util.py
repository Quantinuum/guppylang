import ast
import inspect
import linecache
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from types import FrameType
from typing import ClassVar

from guppylang_internals.ast_util import annotate_location
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnsupportedError,
)
from guppylang_internals.definition.common import (
    DefId,
    UnknownSourceError,
)
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.error import GuppyError
from guppylang_internals.ipython_inspect import is_running_ipython
from guppylang_internals.span import SourceMap, Span, to_span
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.ty import Type

if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter


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
        "{class_type} `{class_name}` already contains a field named `{field_name}`"
    )
    class_name: str
    field_name: str
    class_type: str = "Struct"


@dataclass(frozen=True)
class NonGuppyMethodError(Error):
    title: ClassVar[str] = "Not a Guppy method"
    span_label: ClassVar[str] = (
        "Method `{method_name}` of {class_type} `{class_name}` is not a Guppy function"
    )
    class_name: str
    method_name: str
    class_type: str

    @dataclass(frozen=True)
    class Suggestion(Help):
        message: ClassVar[str] = (
            "Add a `@guppy` annotation to turn `{method_name}` into a Guppy method"
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(NonGuppyMethodError.Suggestion(None))


@dataclass(frozen=True)
class RepeatedTypeParamError(Error):
    title: ClassVar[str] = "Duplicate type parameter"
    span_label: ClassVar[str] = "Type parameter `{name}` cannot be used multiple times"
    name: str


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


# TODO: Most all the function are about parsing ASTs, should they be moved to a
#  common utility module (parsing.py?)
def parse_source(source_lines: list[str], line_offset: int) -> tuple[str, ast.AST, int]:
    """Parses a list of source lines into an AST object.

    Also takes care of correctly parsing source that is indented.

    Returns the full source, the parsed AST node, and a potentially updated line number
    offset.
    """
    source = "".join(source_lines)  # Lines already have trailing \n's
    if source_lines[0][0].isspace():
        # This means the function is indented, so we cannot parse it straight away.
        # Running `textwrap.dedent` would mess up the column number in spans. Instead,
        # we'll just wrap the source into a dummy class definition so the indent becomes
        # valid
        cls_node = ast.parse("class _:\n" + source).body[0]
        assert isinstance(cls_node, ast.ClassDef)
        node = cls_node.body[0]
        line_offset -= 1
    else:
        node = ast.parse(source).body[0]
    return source, node, line_offset


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


def extract_generic_params(
    cls_def: ast.ClassDef, class_name: str, globals: Globals, class_kind: str
) -> list[Parameter]:
    """Extracts generic parameters from a class definition."""
    params = []
    params_span: Span | None = None

    # Look for generic parameters from Python 3.12 style syntax
    if sys.version_info >= (3, 12):
        if cls_def.type_params:
            first, last = cls_def.type_params[0], cls_def.type_params[-1]
            params_span = Span(to_span(first).start, to_span(last).end)
            param_vars_mapping: dict[str, Parameter] = {}
            for idx, param_node in enumerate(cls_def.type_params):
                param = parse_parameter(param_node, idx, globals, param_vars_mapping)
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
                err: Error = RedundantParamsError(base, class_name)
                err.add_sub_diagnostic(RedundantParamsError.PrevSpec(params_span))
                raise GuppyError(err)
            params = params_from_ast(elems, globals)
        case bases:
            err = UnsupportedError(
                bases[0],
                f"{class_kind} inheritance",
                singular=True,
            )
            raise GuppyError(err)

    return params


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
