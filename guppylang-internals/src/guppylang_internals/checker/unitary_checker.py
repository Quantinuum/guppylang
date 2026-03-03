import ast

from guppylang_internals.ast_util import find_nodes, get_type, loop_in_ast
from guppylang_internals.checker.cfg_checker import CheckedBB, CheckedCFG
from guppylang_internals.checker.core import Place, contains_subscript
from guppylang_internals.checker.errors.generic import (
    InvalidUnderDagger,
    UnsupportedError,
)
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError, GuppyTypeError
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

    def check(self, bb: CheckedBB[Place], unitary_flags: UnitaryFlags) -> None:
        self.flags = unitary_flags
        for stmt in bb.statements:
            self.visit(stmt)

    def _check_classical_args(self, args: list[ast.expr]) -> bool:
        for arg in args:
            self.visit(arg)
            if contain_qubit_ty(get_type(arg)):
                return False
        return True

    def _check_call(self, node: AnyCall, ty: FunctionType) -> None:
        classic = self._check_classical_args(node.args)
        flag_ok = self.flags in ty.unitary_flags
        if not classic and not flag_ok:
            raise GuppyTypeError(
                UnitaryCallError(node, self.flags & (~ty.unitary_flags))
            )

    def visit_GlobalCall(self, node: GlobalCall) -> None:
        func = ENGINE.get_parsed(node.def_id)
        assert isinstance(func, CallableDef)
        self._check_call(node, func.ty)

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
            raise GuppyError(InvalidUnderDagger(node, "Assignment"))
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
    bb_checker = BBUnitaryChecker()
    for bb in cfg.bbs:
        bb_checker.check(bb, unitary_flags)
