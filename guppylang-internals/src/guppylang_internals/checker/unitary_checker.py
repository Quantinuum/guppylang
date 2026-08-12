import ast
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

from guppylang_internals.ast_util import branching_in_ast, get_type, loop_in_ast
from guppylang_internals.cfg.bb import BBStatement
from guppylang_internals.checker.cfg_checker import CheckedCFG
from guppylang_internals.checker.core import Place
from guppylang_internals.checker.errors.generic import InvalidUnderDagger
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError, GuppyTypeError
from guppylang_internals.nodes import (
    AbortExpr,
    AnyCall,
    BarrierExpr,
    CheckedModifiedBlock,
    GlobalCall,
    LocalCall,
    ModifiedBlock,
    StateOutputExpr,
    TensorCall,
)
from guppylang_internals.span import ToSpan
from guppylang_internals.tys.errors import UnitaryCallError
from guppylang_internals.tys.qubit import contain_qubit_ty
from guppylang_internals.tys.ty import (
    FunctionType,
    UnitaryFlags,
)


class InvalidUnitaryKind(Enum):
    MissingCtrlDaggered = auto()
    MissingCtrlDaggeredForFlag = auto()
    MissingCtrl = auto()


@dataclass(frozen=True)
class InvalidUnitaryError(Error):
    title: ClassVar[str] = "Invalid `@guppy.unitary` implementation"
    kind: InvalidUnitaryKind
    implementation: str | None = None
    flag: str | None = None

    @property
    def rendered_message(self) -> str:
        match self.kind:
            case InvalidUnitaryKind.MissingCtrlDaggered:
                return (
                    "A `@guppy.unitary` class implementing `daggered` and `controlled` "
                    "requires either a `ctrl_daggered` implementation or `unitary=True`"
                    " on `__call__`"
                )
            case InvalidUnitaryKind.MissingCtrlDaggeredForFlag:
                assert self.implementation is not None
                assert self.flag is not None
                return (
                    f"A `@guppy.unitary` class implementing `{self.implementation}` for"
                    f" a function marked `{self.flag}=True` requires either a "
                    "`ctrl_daggered` implementation or `unitary=True` on `__call__`"
                )
            case InvalidUnitaryKind.MissingCtrl:
                return (
                    "A `@guppy.unitary` class implementing `ctrl_daggered` "
                    "implementation requires either a  `controlled` implementation or "
                    "`controllable=True` on `__call__`"
                )


def check_invalid_under_dagger(
    def_node: ast.FunctionDef | ModifiedBlock, unitary_flags: UnitaryFlags
) -> None:
    """Check that there are no invalid constructs in a daggered CFG."""
    if UnitaryFlags.Dagger not in unitary_flags:
        return

    if isinstance(def_node, ast.FunctionDef):
        stmt_list = def_node.body
    else:
        # When analyzing a `ModifiedBlock` we need the original AST before
        # the builder transforms it
        stmt_list = def_node.original_ast_body
        assert stmt_list is not None, (
            "original_ast_body should not be None for a daggered block"
        )

    for stmt in stmt_list:
        # we do not want to recursively check inside nested `with` blocks
        if isinstance(stmt, ast.With):
            continue
        loops = loop_in_ast(stmt)
        if len(loops) != 0:
            loop = next(iter(loops))
            _raise_invalid_under_dagger(loop, def_node, "Loop", unitary_flags)
        branches = branching_in_ast(stmt)
        if len(branches) != 0:
            branch = next(iter(branches))
            _raise_invalid_under_dagger(branch, def_node, "Branch", unitary_flags)


def _raise_invalid_under_dagger(
    span: ToSpan,
    node: ast.FunctionDef | ModifiedBlock,
    things: str,
    unitary_flags: UnitaryFlags,
) -> None:
    err = InvalidUnderDagger(span, things)
    if isinstance(node, ModifiedBlock):
        err.add_sub_diagnostic(InvalidUnderDagger.Dagger(node.span_ctxt_manager()))
    elif isinstance(node, ast.FunctionDef):
        err.add_sub_diagnostic(
            InvalidUnderDagger.FunctionHelp(None, node.name, unitary_flags)
        )
    err.add_sub_diagnostic(InvalidUnderDagger.ControlFlowHelp(None))

    raise GuppyError(err)


class BBUnitaryChecker(ast.NodeVisitor):
    """AST visitor that checks whether the modifiers (dagger, control, power)
    are applicable."""

    flags: UnitaryFlags

    def check(
        self,
        statements: list[BBStatement] | list[ast.expr],
        unitary_flags: UnitaryFlags,
    ) -> None:
        self.flags = unitary_flags
        for stmt in statements:
            self.visit(stmt)

    def _check_args(self, args: list[ast.expr]) -> bool:
        """Recursively checks the arguments of a call.
        Returns True if the call is classical"""
        for arg in args:
            self.visit(arg)
        return all(not contain_qubit_ty(get_type(arg)) for arg in args)

    def _check_call(
        self, node: AnyCall, call_ty: FunctionType, func: CallableDef | None = None
    ) -> None:
        """
        `func`: it's only used for a better error message when the call is a GlobalCall.
        Is None for LocalCall and TensorCall.
        """
        # NICOLA: TODO: Consider using CustomModifiedHint

        # If we are under any modifier, we cannot allocate qubits
        if contain_qubit_ty(call_ty.output) and self.flags != UnitaryFlags.NoFlags:
            err = UnitaryCallError(node, self.flags, missing_keyword_hint=False)
            err.add_sub_diagnostic(UnitaryCallError.QubitAllocationNote(None))
            raise GuppyError(err)

        # If the function has quantum i/o, the flags must be compatible with the
        # function's unitary flags. Otherwise, if the function is classical, we only
        # need to check that if we are in dagger (or unitary) context, the function
        # is daggerable.
        is_classic_fun = self._check_args(node.args)
        if is_classic_fun:
            if UnitaryFlags.Dagger not in self.flags:
                is_a_valid_call = True
            else:
                is_a_valid_call = UnitaryFlags.Dagger in call_ty.unitary_flags
        else:
            is_a_valid_call = self.flags in call_ty.unitary_flags

        if not is_a_valid_call:
            from guppylang_internals.definition.custom import CustomFunctionDef

            # We want the hint only for non-custom functions, since custom
            # functions are usually quantum operations (e.g. gates or measurement)
            if isinstance(func, CustomFunctionDef):
                err = UnitaryCallError(
                    node,
                    self.flags & (~call_ty.unitary_flags),
                    missing_keyword_hint=True,
                )
            else:
                if func is not None:
                    err = UnitaryCallError(
                        node,
                        self.flags & (~call_ty.unitary_flags),
                        missing_keyword_hint=False,
                    )
                    from guppylang_internals.definition.pytket_circuits import (
                        ParsedPytketDef,
                    )

                    if isinstance(func, ParsedPytketDef):
                        err.add_sub_diagnostic(
                            UnitaryCallError.PytketHint(None, func.name)
                        )
                    else:
                        err.add_sub_diagnostic(
                            UnitaryCallError.MissingFlagHint(None, func.name)
                        )
                else:
                    # If func is None, we are checking a higher-order call
                    missing_flags = self.flags & (~call_ty.unitary_flags)
                    err = UnitaryCallError(
                        node,
                        missing_flags,
                        missing_keyword_hint=False,
                    )
                    err.add_sub_diagnostic(
                        UnitaryCallError.HigherOrderHint(
                            None,
                            missing_flags.callable_name(),
                            "higher-order"
                            if call_ty.unitary_flags == UnitaryFlags.NoFlags
                            else call_ty.unitary_flags.callable_name(),
                        )
                    )
            raise GuppyTypeError(err)

    def visit_GlobalCall(self, node: GlobalCall) -> None:
        func = ENGINE.get_parsed(node.def_id)
        assert isinstance(func, CallableDef)
        self._check_call(node, func.ty, func)

    def visit_LocalCall(self, node: LocalCall) -> None:
        func = get_type(node.func)
        assert isinstance(func, FunctionType)
        self._check_call(node, func)

    def visit_TensorCall(self, node: TensorCall) -> None:
        self._check_call(node, node.tensor_ty)

    def visit_BarrierExpr(self, node: BarrierExpr) -> None:
        # Barrier is always allowed
        pass

    def visit_StateOutputExpr(self, node: StateOutputExpr) -> None:
        # State output is not allowed under dagger, since the execution order
        # is not guaranteed
        if UnitaryFlags.Dagger in self.flags:
            raise GuppyTypeError(
                UnitaryCallError(
                    node,
                    self.flags,
                    missing_keyword_hint=True,
                )
            )

    def visit_AbortExpr(self, node: AbortExpr) -> None:
        # panics and exits are not allowed under dagger, since the execution order
        # is not guaranteed
        if UnitaryFlags.Dagger in self.flags:
            raise GuppyTypeError(
                UnitaryCallError(
                    node,
                    self.flags,
                    missing_keyword_hint=True,
                )
            )
        self.visit(node.signal)
        self.visit(node.msg)
        for value in node.values:
            self.visit(value)

    def visit_CheckedModifiedBlock(self, node: CheckedModifiedBlock) -> None:
        # Nested modified blocks are checked separately by the CFG checker
        pass

    def _check_assign(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> None:
        if node.value is not None:
            self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_assign(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_assign(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_assign(node)


def check_cfg_unitary(
    cfg: CheckedCFG[Place],
    unitary_flags: UnitaryFlags,
) -> None:
    """Checks that the given unitary flags are valid for a CFG."""
    # If no UnitaryFlags are present, we do no need to check unitarity
    if unitary_flags == UnitaryFlags.NoFlags:
        return

    bb_checker = BBUnitaryChecker()
    for bb in cfg.bbs:
        bb_checker.check(bb.statements, unitary_flags)


def check_modified_def_combinations(
    unitary_flags: UnitaryFlags,
    *,
    definition_span: ToSpan | None = None,
    has_daggered: bool,
    has_controlled: bool,
    has_ctrl_daggered: bool,
) -> None:
    """Check that custom unitary modifier implementations form a valid set.

    We require:
    - If a function has both `daggered` and `controlled` implementations, it must
      also have a `ctrl_daggered` implementation, unless the function is marked
      as `unitary=True`.
    - If a function is marked as `controllable=True` and has a `daggered`
      implementation, it must also have a `ctrl_daggered` implementation
      or the function is marked as `unitary=True`.
    - If a function is marked as `daggerable=True` and has a `controlled`
      implementation, it must also have a `ctrl_daggered` implementation
      or the function is marked as `unitary=True`.
    - If a function has a `ctrl_daggered` implementation, it must also have
      a `controlled` implementation, unless the function is marked as
      `controllable=True`.
    """
    # Custom daggered and controlled implementations require ctrl_daggered support.
    if (
        has_daggered
        and has_controlled
        and not has_ctrl_daggered
        and unitary_flags != UnitaryFlags.Unitary
    ):
        raise GuppyError(
            InvalidUnitaryError(definition_span, InvalidUnitaryKind.MissingCtrlDaggered)
        )
    if not has_ctrl_daggered and unitary_flags != UnitaryFlags.Unitary:
        # Controllable plus a custom daggered implementation requires ctrl_daggered.
        if has_daggered and UnitaryFlags.Control in unitary_flags:
            raise GuppyError(
                InvalidUnitaryError(
                    definition_span,
                    InvalidUnitaryKind.MissingCtrlDaggeredForFlag,
                    "daggered",
                    "controllable",
                )
            )
        # Daggerable plus a custom controlled implementation requires ctrl_daggered.
        if has_controlled and UnitaryFlags.Dagger in unitary_flags:
            raise GuppyError(
                InvalidUnitaryError(
                    definition_span,
                    InvalidUnitaryKind.MissingCtrlDaggeredForFlag,
                    "controlled",
                    "daggerable",
                )
            )

    # A custom ctrl_daggered implementation requires controllable support.
    if (
        has_ctrl_daggered
        and not has_controlled
        and UnitaryFlags.Control not in unitary_flags
    ):
        raise GuppyError(
            InvalidUnitaryError(definition_span, InvalidUnitaryKind.MissingCtrl)
        )
