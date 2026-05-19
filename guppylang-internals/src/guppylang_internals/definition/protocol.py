import ast
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    UnexpectedError,
    UnsupportedError,
)
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    Definition,
    ParsableDef,
)
from guppylang_internals.definition.declaration import ParsedFunctionDecl
from guppylang_internals.definition.util import (
    NonGuppyMethodError,
    RedundantParamsError,
    params_from_ast,
    parse_py_class,
    try_parse_generic_base,
)
from guppylang_internals.diagnostic import Help
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.span import SourceMap, Span, to_span
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.ty import FunctionType

if TYPE_CHECKING:
    from guppylang_internals.diagnostic import Error

if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter


@dataclass(frozen=True)
class ProtocolDef(Definition):
    """Abstract base class for protocol definitions."""

    description: str = field(default="protocol", init=False)


@dataclass(frozen=True)
class EmptyBodyHint(Help):
    message: ClassVar[str] = "The body of protocol function definitions must be empty"


@dataclass(frozen=True)
class NoAnnotationHint(Help):
    message: ClassVar[str] = "Protocol function definitions don't need to be annotated"


@dataclass(frozen=True)
class RawProtocolDef(ProtocolDef, ParsableDef):
    """A raw protocol definition that has not been parsed yet."""

    python_class: type

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedProtocolDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        # Mostly copied from RawStructDef.parse, but only allowing function declarations
        # in the body and allowing `Protocol` as a base class.
        frame = DEF_STORE.frames[self.id]
        cls_def = parse_py_class(self.python_class, frame, sources)
        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        # Look for generic parameters from Python 3.12 style syntax.
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

        match cls_def.bases:
            case []:
                pass
            # We allow `Generic[...]` or `Protocol[...]` to specify  parameters with the
            # legacy syntax.
            case [base] if elems := try_parse_generic_base(
                base, "Generic"
            ) or try_parse_generic_base(base, "Protocol"):
                # Complain if we already have Python 3.12 generic params
                if params_span is not None:
                    err: Error = RedundantParamsError(base, self.name)
                    err.add_sub_diagnostic(RedundantParamsError.PrevSpec(params_span))
                    raise GuppyError(err)
                params = params_from_ast(elems, globals)
            # Specifying `Protocol` is redundant but we allow it optionally.
            case [base] if isinstance(base, ast.Name) and base.id == "Protocol":
                pass
            case bases:
                err = UnsupportedError(bases[0], "Protocol inheritance", singular=True)
                raise GuppyError(err)

        func_defs = {}
        for i, node in enumerate(cls_def.body):
            match i, node:
                # Docstrings are fine if they occur at the start.
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # Parse the function definitions into types.
                case _, ast.FunctionDef(name=name) as node:
                    from guppylang.defs import GuppyDefinition

                    py_func = getattr(self.python_class, name, None)

                    if not isinstance(py_func, GuppyDefinition):
                        raise GuppyError(
                            NonGuppyMethodError(
                                node, self.name, name, "protocol", "@guppy.require"
                            )
                        )
                    assert isinstance(py_func, GuppyDefinition)
                    func_defs[name] = py_func.id
                # Fields are not allowed in protocols.
                case _, ast.AnnAssign(target=ast.Name(_)) as node:
                    err = UnsupportedError(
                        node, "Fields", unsupported_in="a protocol definition"
                    )
                    raise GuppyError(err)
                case _, node:
                    err = UnexpectedError(
                        node, "statement", unexpected_in="protocol definition"
                    )
                    raise GuppyError(err)

        return ParsedProtocolDef(self.id, self.name, cls_def, params, func_defs)


@dataclass(frozen=True)
class ParsedProtocolDef(ProtocolDef, CheckableDef):
    """A protocol definition where members have been parsed but not checked yet."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    members: Mapping[str, DefId]

    def check(self, globals: Globals) -> "CheckedProtocolDef":
        """Checks the member function types and returns a checked definition."""
        # It would be nice to check here that all of the methods are well
        # formed, but they're all already individually queued in the engine.
        return CheckedProtocolDef(
            self.id, self.name, self.defined_at, self.params, self.members
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> ProtocolInst:
        """Checks if the protocol can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return ProtocolInst(tuple(args), self.id)


@dataclass(frozen=True)
class CheckedProtocolDef(ProtocolDef, CompiledDef):
    """A fully checked protocol definition."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    member_defs: Mapping[str, DefId]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> ProtocolInst:
        """Checks if the protocol can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return ProtocolInst(tuple(args), self.id)

    def member_sig(self, name: str) -> FunctionType:
        def_ = ENGINE.get_parsed(self.member_defs[name])
        assert isinstance(def_, ParsedFunctionDecl)
        return def_.ty
