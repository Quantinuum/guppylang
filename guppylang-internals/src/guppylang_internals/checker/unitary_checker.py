import ast

from guppylang_internals.ast_util import find_nodes, get_type, loop_in_ast
from guppylang_internals.cfg.bb import BBStatement
from guppylang_internals.checker.cfg_checker import CheckedCFG
from guppylang_internals.checker.core import Place, contains_subscript
from guppylang_internals.checker.errors.generic import (
    InvalidUnderDagger,
    UnsupportedError,
)
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang_internals.nodes import (
    AnyCall,
    BarrierExpr,
    GlobalCall,
    LocalCall,
    PlaceNode,
    StateResultExpr,
    TensorCall,
)
from guppylang_internals.tys.errors import UnitaryCallError
from guppylang_internals.tys.qubit import contain_qubit_ty
from guppylang_internals.tys.ty import FunctionType, UnitaryFlags


def check_invalid_under_dagger(
    fn_def: ast.FunctionDef, unitary_flags: UnitaryFlags
) -> None:
    """Check that there are no invalid constructs in a daggered CFG.
    This checker checks the case the UnitaryFlags is given by
    annotation (i.e., not inferred from `with dagger:`).
    """
    if UnitaryFlags.Dagger not in unitary_flags:
        return

    for stmt in fn_def.body:
        loops = loop_in_ast(stmt)
        if len(loops) != 0:
            loop = next(iter(loops))
            err = InvalidUnderDagger(loop, "Loop")
            raise GuppyError(err)
            # Note: sub-diagnostic for dagger context is not available here

        found = find_nodes(
            lambda n: isinstance(n, ast.Assign | ast.AnnAssign | ast.AugAssign),
            stmt,
            {ast.FunctionDef},
        )
        if len(found) != 0:
            assign = next(iter(found))
            err = InvalidUnderDagger(assign, "Assignment")
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
            err = UnitaryCallError(node, self.flags & (~ty.unitary_flags))
            if func is not None:
                from guppylang_internals.definition.custom import CustomFunctionDef

                if not isinstance(func, CustomFunctionDef):
                    # We want the hint only for non-custom functions, since for custom
                    # functions are usually quantum operations, such as gates or
                    # measurement
                    err.add_sub_diagnostic(UnitaryCallError.Hint(None, func.name))
            raise GuppyTypeError(err)

        # If we are under any modifier, we cannot allocate qubits
        if contain_qubit_ty(ty.output) and self.flags != UnitaryFlags.NoFlags:
            err = UnitaryCallError(node, self.flags)
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

    def visit_StateResultExpr(self, node: StateResultExpr) -> None:
        # StateResult is always allowed
        pass

    def _check_assign(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> None:
        if UnitaryFlags.Dagger in self.flags:
            raise InternalGuppyError("Dagger conditions should already be checked")
        if node.value is not None:
            self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_assign(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_assign(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_assign(node)

    def visit_PlaceNode(self, node: PlaceNode) -> None:
        if UnitaryFlags.Dagger in self.flags and contains_subscript(node.place):
            raise GuppyError(
                UnsupportedError(node, "index access", True, "dagger context")
            )


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
