import ast
from typing import TYPE_CHECKING

from guppylang_internals.ast_util import branching_in_ast, get_type, loop_in_ast
from guppylang_internals.cfg.bb import BBStatement
from guppylang_internals.checker.cfg_checker import CheckedCFG
from guppylang_internals.checker.core import Place
from guppylang_internals.checker.errors.generic import ExpectedError, InvalidUnderDagger
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError, GuppyTypeError
from guppylang_internals.nodes import (
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
from guppylang_internals.tys.builtin import (
    get_array_length,
    get_element_type,
    is_array_type,
)
from guppylang_internals.tys.const import BoundConstVar
from guppylang_internals.tys.errors import UnitaryCallError
from guppylang_internals.tys.param import ConstParam
from guppylang_internals.tys.qubit import contain_qubit_ty, is_qubit_ty
from guppylang_internals.tys.ty import (
    FunctionType,
    UnitaryFlags,
    unify,
)

if TYPE_CHECKING:
    from guppylang_internals.definition.function import ParsedModifiedDefs


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

    def _check_classical_args(self, args: list[ast.expr]) -> bool:
        for arg in args:
            self.visit(arg)
            if contain_qubit_ty(get_type(arg)):
                return False
        return True

    def _check_call(
        self, node: AnyCall, ty: FunctionType, func: CallableDef | None = None
    ) -> None:
        """
        `func`: it's only used for a better error message when the call is a GlobalCall.
        Is None for LocalCall and TensorCall.
        """
        classic_args = self._check_classical_args(node.args)
        flag_ok = self.flags in ty.unitary_flags
        if not classic_args and not flag_ok:
            from guppylang_internals.definition.custom import CustomFunctionDef
            from guppylang_internals.definition.function import ParsedFunctionDef

            # We want the hint only for non-custom functions, since custom
            # functions are usually quantum operations (e.g. gates or measurement)
            if isinstance(func, CustomFunctionDef):
                err = UnitaryCallError(
                    node,
                    self.flags & (~ty.unitary_flags),
                    missing_keyword_hint=True,
                )
            elif func is not None:
                err = UnitaryCallError(
                    node,
                    self.flags & (~ty.unitary_flags),
                    missing_keyword_hint=False,
                )
                if (
                    isinstance(func, ParsedFunctionDef)
                    and func.parsed_modified_defs is not None
                ):
                    # NICOLA TODO: this error must be improved
                    err.add_sub_diagnostic(
                        UnitaryCallError.CustomModifiedHint(None, func.name)
                    )
                else:
                    err.add_sub_diagnostic(
                        UnitaryCallError.MissingFlagHint(None, func.name)
                    )
            else:
                # If func is None, we are checking a higher-order call
                missing_flags = self.flags & (~ty.unitary_flags)
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
                        if ty.unitary_flags == UnitaryFlags.NoFlags
                        else ty.unitary_flags.callable_name(),
                    )
                )

            raise GuppyTypeError(err)

        # If we are under any modifier, we cannot allocate qubits
        if contain_qubit_ty(ty.output) and self.flags != UnitaryFlags.NoFlags:
            err = UnitaryCallError(node, self.flags, missing_keyword_hint=False)
            err.add_sub_diagnostic(UnitaryCallError.QubitAllocationNote(None))
            raise GuppyError(err)

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
        # StateOutput is always allowed
        pass

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


def check_modified_def_signature(
    parsed_modified_defs: "ParsedModifiedDefs", parent_ty: FunctionType
) -> None:
    if parsed_modified_defs.call_daggered:
        daggered_ty = parsed_modified_defs.call_daggered.ty
        if unify(parent_ty, daggered_ty, {}) is None:
            # NICOLA: TODO the error message is garbage
            raise GuppyError(
                ExpectedError(
                    parsed_modified_defs.call_daggered.defined_at,
                    f"signature compatible with {parent_ty}",
                )
            )

    if parsed_modified_defs.call_controlled:
        _check_controlled_def_signature(
            parsed_modified_defs.call_controlled.ty,
            parent_ty,
            parsed_modified_defs.call_controlled.defined_at,
        )
    if parsed_modified_defs.call_ctrl_daggered:
        _check_controlled_def_signature(
            parsed_modified_defs.call_ctrl_daggered.ty,
            parent_ty,
            parsed_modified_defs.call_ctrl_daggered.defined_at,
        )


def _check_controlled_def_signature(
    modified_ty: FunctionType, parent_ty: FunctionType, defined_at: ast.FunctionDef
) -> None:
    expected_ty = FunctionType(
        # last input must be the array of control qubits
        modified_ty.inputs[:-1],
        modified_ty.output,
        # last param must be parameter for the number of control qubits
        modified_ty.params[:-1],
        modified_ty.comptime_args,
        modified_ty.unitary_flags,
    )
    if unify(expected_ty, parent_ty, {}) is None:
        raise GuppyError(
            # NICOLA: TODO the error message is garbage
            ExpectedError(
                defined_at,
                f"signature compatible with {parent_ty}",
            )
        )

    if not modified_ty.inputs or not modified_ty.params:
        raise GuppyError(
            ExpectedError(
                defined_at,
                "signature with final input of type `array[qubit, n]`",
            )
        )

    last_input_ty = modified_ty.inputs[-1].ty
    last_param = modified_ty.params[-1]
    if (
        not is_array_type(last_input_ty)
        or not is_qubit_ty(get_element_type(last_input_ty))
        or not isinstance(last_param, ConstParam)
        or get_array_length(last_input_ty)
        != BoundConstVar(last_param.ty, last_param.name, last_param.idx)
    ):
        raise GuppyError(
            ExpectedError(
                defined_at,
                "signature with final input of type `array[qubit, n]`",
            )
        )
