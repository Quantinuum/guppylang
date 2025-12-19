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
from guppylang_internals.definition.struct import (
    RedundantParamsError,
    params_from_ast,
    parse_py_class,
    try_parse_generic_base,
)


if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter


# TODO: Considering renaming to UncheckedField and CheckedField,
# and joining with UncheckedStructField and StructField
@dataclass(frozen=True)
class UncheckedEnumField:
    """A single field on a enum whose type has not been checked yet."""

    name: str
    type_ast: ast.expr


@dataclass(frozen=True)
class EnumField:
    """A single field on a struct."""

    name: str
    ty: Type


@dataclass(frozen=True)
class RawEnumDef(TypeDef, ParsableDef):
    """A raw enum type definition before parsing."""

    print("ciaociao")
    python_class: type
    params: None = field(default=None, init=False)  # Params not known yet

    def parse(self, globals: "Globals", sources: SourceMap) -> ParsedEnumDef:
        """Parses the raw class object into an AST and checks that it is well-formed."""
        print("ciaociao I'm parsing enum")
        frame = DEF_STORE.frames[self.id]
        """
        cls_node = ast.parse("class _:\n" + source).body[0]
        assert isinstance(cls_node, ast.ClassDef)
        cls_def = cls_node.body[0]
        """
        cls_def = parse_py_class(self.python_class, frame, sources)
        print(cls_def)
        print("----")

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
        # Assuming is the same...
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
                err = UnsupportedError(bases[0], "Enum inheritance", singular=True)
                raise GuppyError(err)

        # we look for fields in the class body
        fields: list[UncheckedEnumField] = []
        used_field_names: set[str] = set()
        used_func_names: dict[str, ast.FunctionDef] = {}
        for i, node in enumerate(cls_def.body):
            match i, node:
                # TODO: do we allow `pass` statements to define empty enum?
                case _, ast.Pass():
                    pass
                # Docstrings are also fine if they occur at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # We do not allow methods, for now
                case _, ast.FunctionDef(name=name) as node:
                    # TODO: UnsupportedError or UnexpectedError?
                    err = UnsupportedError(node.value, "methods", singular=False)
                    err.extra = " in Guppy enum definitions"
                    raise GuppyError(err)

                # hereeeee
                # Struct fields are declared via annotated assignments without value
                case _, ast.AnnAssign(target=ast.Name(id=field_name)) as node:
                    if node.value:
                        err = UnsupportedError(node.value, "methods", singular=False)
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

        return ParsedEnumDef(self.id, self.name, cls_def, params, fields)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw enum definition")


@dataclass(frozen=True)
class ParsedEnumDef(TypeDef, CheckableDef):
    """
    Docstring for ParsedEnumDef
    """

    pass
