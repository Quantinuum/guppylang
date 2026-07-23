import ast
import copy
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar, NamedTuple, NoReturn

from hugr import Wire
from typing_extensions import override

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Context
from guppylang_internals.checker.expr_checker import ExprSynthesizer
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.definition.common import (
    DefId,
)
from guppylang_internals.definition.custom import CustomFunctionDef
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
)
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import (
    BypassOverloadError,
    GuppyError,
    InternalGuppyError,
)
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys import Effect
from guppylang_internals.tys.printing import signature_to_str
from guppylang_internals.tys.subst import Subst
from guppylang_internals.tys.ty import FunctionType, Type


class OverloadVariant(NamedTuple):
    func_ty: FunctionType
    has_var_args: bool


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
    variants: list[OverloadVariant]

    @property
    def rendered_message(self) -> str:
        return "Available overloads are:\n" + "\n".join(
            f"  {signature_to_str(self.func_name, sig.func_ty, sig.has_var_args)}"
            for sig in self.variants
        )


@dataclass(frozen=True)
class OverloadHigherOrderError(Error):
    title: ClassVar[str] = "Higher-order overloaded function"
    span_label: ClassVar[str] = (
        "Overloaded function `{func}` may not be used as a higher-order value"
    )
    func: str


@dataclass(frozen=True)
class InternalExpectOverloadError(Error):
    title: ClassVar[str] = "Expected overload error"
    span_label: ClassVar[str] = (
        "Error should have been caught and replaced by overload error"
    )


@dataclass(frozen=True)
class OverloadedFunctionDef(CompiledCallableDef, CallableDef):
    func_ids: list[DefId]
    description: str = field(default="overloaded function", init=False)

    @property
    def call_effects(self) -> Iterable[Effect]:
        raise InternalGuppyError("Should have been resolved to one overload")

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        raise GuppyError(OverloadHigherOrderError(node, self.name))

    @override
    def check_call(
        self, args: list[ast.expr], ty: Type, node: ast.Call, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        new_node, subst = self._try_overloads(
            args,
            node,
            ctx,
            checking=True,
            ty=ty,
        )
        return new_node, subst

    @override
    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Type]:
        new_node, ty = self._try_overloads(
            args,
            node,
            ctx,
            checking=False,
        )
        return new_node, ty

    def resolve_overload(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> CallableDef | None:
        """Resolves an overload usage to a specific function definition based on the
        provided arguments. Returns None if no matching overload can be synthesized."""
        for def_id in self.func_ids:
            defn = ctx.globals[def_id]
            assert isinstance(defn, CallableDef)
            try:
                # synthesize_call may modify args and node,
                # thus we deepcopy them before passing in the function
                node_copy = copy.deepcopy(node)
                args_copy = copy.deepcopy(args)
                defn.synthesize_call(args_copy, node_copy, ctx)
            except GuppyError:
                continue
            else:
                return defn
        return None

    def _try_overloads(
        self,
        args: list[ast.expr],
        node: AstNode,
        ctx: Context,
        checking: bool,
        ty: Type | None = None,
    ) -> tuple[ast.expr, Any]:
        available_sigs: list[OverloadVariant] = []
        bypass_error: BypassOverloadError | None = None
        for def_id in self.func_ids:
            defn = ctx.globals[def_id]
            assert isinstance(defn, CallableDef)
            has_var_args = isinstance(defn, CustomFunctionDef) and defn.has_var_args
            hidden_from_hints = isinstance(defn, CustomFunctionDef) and getattr(
                defn.call_checker, "exclude_from_overload_hints", False
            )
            if not hidden_from_hints:
                available_sigs.append(OverloadVariant(defn.ty, has_var_args))
            try:
                # synthesize_call may modify args and node,
                # thus we deepcopy them before passing in the function
                node_copy = copy.deepcopy(node)
                args_copy = copy.deepcopy(args)
                if checking:
                    assert ty is not None
                    return defn.check_call(args_copy, ty, node_copy, ctx)
                return defn.synthesize_call(args_copy, node_copy, ctx)
            except BypassOverloadError as e:
                bypass_error = e
                continue
            except GuppyError:
                continue
        if bypass_error is not None:
            return self._call_bypass_error(bypass_error, available_sigs)
        return self._call_error(args, node, ctx, available_sigs, ty)

    def _call_bypass_error(
        self,
        err: BypassOverloadError,
        available_sigs: list[OverloadVariant],
    ) -> NoReturn:
        err.error.add_sub_diagnostic(
            AvailableOverloadsHint(None, self.name, available_sigs)
        )
        raise err

    def _call_error(
        self,
        args: list[ast.expr],
        node: AstNode,
        ctx: "Context",
        available_sigs: list[OverloadVariant],
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

    @override
    def compile_call(
        self,
        args: list[Wire],
        dfg: "DFContainer",
        ctx: "CompilerContext",
        node: AstNode,
    ) -> "CallReturnWires":
        # This should never be called: Checking the call replaces it with the concrete
        # implementation
        raise InternalGuppyError(
            "OverloadedFunctionDef.compile_call shouldn't be invoked"
        )
