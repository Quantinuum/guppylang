import ast
import copy
from contextlib import suppress
from dataclasses import dataclass, field
from typing import ClassVar, NoReturn

from hugr import Wire

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Context
from guppylang_internals.checker.expr_checker import ExprSynthesizer
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.definition.common import (
    DefId,
)
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
)
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys.printing import signature_to_str
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import FunctionType, Type


@dataclass(frozen=True)
class OverloadNoMatchError(Error):
    title: ClassVar[str] = "Invalid call of overloaded function"
    func: str
    arg_tys: list[Type]
    return_ty: Type | None

    @property
    def rendered_span_label(self) -> str:
        stem = f"No variant of overloaded function `{self.func}` "
        match self.arg_tys:
            case []:
                stem += "takes 0 arguments"
            case [ty]:
                stem += f"takes a `{ty}` argument"
            case tys:
                args = ", ".join(f"`{ty}`" for ty in tys)
                stem += f"takes arguments {args}"
        if self.return_ty:
            stem += f" and returns `{self.return_ty}`"
        return stem


@dataclass(frozen=True)
class AvailableOverloadsHint(Note):
    func_name: str
    variants: list[FunctionType]

    @property
    def rendered_message(self) -> str:
        return "Available overloads are:\n" + "\n".join(
            f"  {signature_to_str(self.func_name, ty)}" for ty in self.variants
        )


@dataclass(frozen=True)
class OverloadHigherOrderError(Error):
    title: ClassVar[str] = "Higher-order overloaded function"
    span_label: ClassVar[str] = (
        "Overloaded function `{func}` may not be used as a higher-order value"
    )
    func: str


@dataclass(frozen=True)
class OverloadedFunctionDef(CompiledCallableDef, CallableDef):
    func_ids: list[DefId]
    description: str = field(default="overloaded function", init=False)

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        raise GuppyError(OverloadHigherOrderError(node, self.name))

    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        available_sigs: list[FunctionType] = []
        for def_id in self.func_ids:
            defn = ctx.globals[def_id]
            assert isinstance(defn, CallableDef)
            available_sigs.append(defn.ty)
            with suppress(GuppyError):
                # check_call may modify args and node,
                # thus we deepcopy them before passing in the function
                node_copy = copy.deepcopy(node)
                args_copy = copy.deepcopy(args)
                return defn.check_call(args_copy, ty, node_copy, ctx)
        return self._call_error(args, node, ctx, available_sigs, ty)

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Type]:
        available_sigs: list[FunctionType] = []
        for def_id in self.func_ids:
            defn = ctx.globals[def_id]
            assert isinstance(defn, CallableDef)
            available_sigs.append(defn.ty)
            with suppress(GuppyError):
                # synthesize_call may modify args and node,
                # thus we deepcopy them before passing in the function
                node_copy = copy.deepcopy(node)
                args_copy = copy.deepcopy(args)
                return defn.synthesize_call(args_copy, node_copy, ctx)
        return self._call_error(args, node, ctx, available_sigs)

    def _call_error(
        self,
        args: list[ast.expr],
        node: AstNode,
        ctx: "Context",
        available_sigs: list[FunctionType],
        return_ty: Type | None = None,
    ) -> NoReturn:
        if args and not return_ty:
            start = to_span(args[0]).start
            end = to_span(args[-1]).end
            span = Span(start, end)
        else:
            span = to_span(node)

        synth = ExprSynthesizer(ctx)
        arg_tys = [synth.synthesize(arg)[1] for arg in args]
        err = OverloadNoMatchError(span, self.name, arg_tys, return_ty)
        err.add_sub_diagnostic(AvailableOverloadsHint(None, self.name, available_sigs))
        raise GuppyError(err)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: "DFContainer",
        ctx: "CompilerContext",
        node: AstNode,
    ) -> "CallReturnWires":
        # This should never be called: Checking the call replaces it with the concrete
        # implementation
        raise InternalGuppyError(
            "OverloadedFunctionDef.compile_call shouldn't be invoked"
        )

    def load_with_args(
        self,
        type_args: Inst,
        dfg: "DFContainer",
        ctx: "CompilerContext",
        node: AstNode,
    ) -> Wire:
        # This should never be called: During checking we should have already ruled out
        # that overloaded functions are used as higher-order values.
        raise InternalGuppyError(
            "OverloadedFunctionDef.load_with_args shouldn't be invoked"
        )
