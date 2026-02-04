import ast
import functools
from collections.abc import Sequence

from hugr import Wire, ops
from hugr.build.dfg import DfBase

from guppylang_internals.ast_util import AstVisitor, get_type
from guppylang_internals.checker.core import Variable, contains_subscript
from guppylang_internals.compiler.core import (
    CompilerBase,
    CompilerContext,
    DFContainer,
    return_var,
)
from guppylang_internals.compiler.expr_compiler import ExprCompiler
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.nodes import (
    ArrayUnpack,
    CheckedModifiedBlock,
    CheckedNestedFunctionDef,
    IterableUnpack,
    PlaceNode,
    TupleUnpack,
)
from guppylang_internals.std._internal.compiler.array import (
    array_discard_empty,
    array_new,
    array_pop,
)
from guppylang_internals.std._internal.compiler.prelude import build_unwrap
from guppylang_internals.tys.builtin import get_element_type
from guppylang_internals.tys.const import ConstValue
from guppylang_internals.tys.ty import TupleType, Type, type_to_row


class StmtCompiler(CompilerBase, AstVisitor[None]):
    """A compiler for Guppy statements to Hugr"""

    expr_compiler: ExprCompiler

    dfg: DFContainer

    def __init__(self, ctx: CompilerContext):
        super().__init__(ctx)
        self.expr_compiler = ExprCompiler(ctx)

    def compile_stmts(
        self,
        stmts: Sequence[ast.stmt],
        dfg: DFContainer,
    ) -> DFContainer:
        """Compiles a list of basic statements into a dataflow node.

        Note that the `dfg` is mutated in-place. After compilation, the DFG will also
        contain all variables that are assigned in the given list of statements.
        """
        self.dfg = dfg
        for s in stmts:
            self.visit(s)
        return self.dfg

    @property
    def builder(self) -> DfBase[ops.DfParentOp]:
        """The Hugr dataflow graph builder."""
        return self.dfg.builder

    @functools.singledispatchmethod
    def _assign(self, lhs: ast.expr, port: Wire) -> None:
        """Updates the local DFG with assignments."""
        raise InternalGuppyError("Invalid assign pattern in compiler")

    @_assign.register
    def _assign_place(self, lhs: PlaceNode, port: Wire) -> None:
        if subscript := contains_subscript(lhs.place):
            assert subscript.setitem_call is not None
            if subscript.item not in self.dfg:
                self.dfg[subscript.item] = self.expr_compiler.compile(
                    subscript.item_expr, self.dfg
                )
            # If the subscript is nested inside the place, e.g. `xs[i].y = ...`, we
            # first need to lookup `tmp = xs[i]`, assign `tmp.y = ...`, and then finally
            # set `xs[i] = tmp`
            if subscript != lhs.place:
                assert subscript.getitem_call is not None
                # Instead of `tmp` just use `xs[i]` as a "name", the dfg tracker doesn't
                # care about this
                self.dfg[subscript] = self.expr_compiler.compile(
                    subscript.getitem_call, self.dfg
                )
            # Assign to the name `xs[i].y`
            self.dfg[lhs.place] = port
            # Look up `xs[i]` again since it was mutated by the assignment above, then
            # compile a call to `__setitem__` to actually mutate
            self.dfg[subscript.setitem_call.value_var] = self.dfg[subscript]
            self.expr_compiler.visit(subscript.setitem_call.call)
        else:
            self.dfg[lhs.place] = port

    @_assign.register
    def _assign_tuple(self, lhs: TupleUnpack, port: Wire) -> None:
        """Handles assignment where the RHS is a tuple that should be unpacked."""
        # Unpack the RHS tuple
        left, starred, right = lhs.pattern.left, lhs.pattern.starred, lhs.pattern.right
        types = [ty.to_hugr(self.ctx) for ty in type_to_row(get_type(lhs))]
        unpack = self.builder.add_op(ops.UnpackTuple(types), port)
        ports = list(unpack)

        # Assign left and right
        for pat, wire in zip(left, ports[: len(left)], strict=True):
            self._assign(pat, wire)
        if right:
            for pat, wire in zip(right, ports[-len(right) :], strict=True):
                self._assign(pat, wire)

        # Starred assignments are collected into an array
        if starred:
            array_ty = get_type(starred)
            starred_ports = (
                ports[len(left) : -len(right)] if right else ports[len(left) :]
            )
            elt = get_element_type(array_ty).to_hugr(self.ctx)
            array = self.builder.add_op(
                array_new(elt, len(starred_ports)), *starred_ports
            )
            self._assign(starred, array)

    @_assign.register
    def _assign_array(self, lhs: ArrayUnpack, port: Wire) -> None:
        """Handles assignment where the RHS is an array that should be unpacked."""
        # Given an assignment pattern `left, *starred, right`, pop from the left and
        # right, leaving us with the starred array in the middle
        length = lhs.length
        elt_ty = lhs.elt_type.to_hugr(self.ctx)

        def pop(
            array: Wire, length: int, pats: list[ast.expr], from_left: bool
        ) -> tuple[Wire, int]:
            err = "Internal error: unpacking of iterable failed"
            num_pats = len(pats)
            # Pop the number of requested elements from the array
            elts = []
            for i in range(num_pats):
                res = self.builder.add_op(
                    array_pop(elt_ty, length - i, from_left), array
                )
                [elt, array] = build_unwrap(self.builder, res, err)
                elts.append(elt)
            # Assign elements to the given patterns
            for pat, elt in zip(
                pats,
                # Assignments are evaluated from left to right, so we need to assign in
                # reverse order if we popped from the right
                elts if from_left else reversed(elts),
                strict=True,
            ):
                self._assign(pat, elt)
            return array, length - num_pats

        array = port
        array, length = pop(array, length, lhs.pattern.left, True)
        array, length = pop(array, length, lhs.pattern.right, False)
        if lhs.pattern.starred:
            self._assign(lhs.pattern.starred, array)
        else:
            assert length == 0
            self.builder.add_op(array_discard_empty(elt_ty), array)

    @_assign.register
    def _assign_iterable(self, lhs: IterableUnpack, port: Wire) -> None:
        """Handles assignment where the RHS is an iterable that should be unpacked."""
        # Collect the RHS into an array by building the comprehension and then fall back
        # to the array case above
        assert isinstance(lhs.compr.length, ConstValue)
        length = lhs.compr.length.value
        assert isinstance(length, int)

        self.dfg[lhs.rhs_var.place] = port
        array = self.expr_compiler.visit_DesugaredArrayComp(lhs.compr)
        unpack = ArrayUnpack(lhs.pattern, length, lhs.compr.elt_ty)
        self._assign_array(unpack, array)

    def visit_Assign(self, node: ast.Assign) -> None:
        [target] = node.targets
        port = self.expr_compiler.compile(node.value, self.dfg)
        self._assign(target, port)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        assert node.value is not None
        port = self.expr_compiler.compile(node.value, self.dfg)
        self._assign(node.target, port)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Expr(self, node: ast.Expr) -> None:
        self.expr_compiler.compile_row(node.value, self.dfg)

    def visit_Return(self, node: ast.Return) -> None:
        # We turn returns into assignments of dummy variables, i.e. the statement
        # `return e0, e1, e2` is turned into `%ret0 = e0; %ret1 = e1; %ret2 = e2`.
        if node.value is not None:
            return_ty = get_type(node.value)
            port = self.expr_compiler.compile(node.value, self.dfg)

            row: list[tuple[Wire, Type]]
            if isinstance(return_ty, TupleType):
                types = [e.to_hugr(self.ctx) for e in return_ty.element_types]
                unpack = self.builder.add_op(ops.UnpackTuple(types), port)
                row = list(zip(unpack, return_ty.element_types, strict=True))
            else:
                row = [(port, return_ty)]

            for i, (wire, ty) in enumerate(row):
                var = Variable(return_var(i), ty, node.value)
                self.dfg[var] = wire

    def visit_CheckedNestedFunctionDef(self, node: CheckedNestedFunctionDef) -> None:
        from guppylang_internals.compiler.func_compiler import compile_local_func_def

        var = Variable(node.name, node.ty, node)
        loaded_func = compile_local_func_def(node, self.dfg, self.ctx)
        self.dfg[var] = loaded_func

    def visit_CheckedModifiedBlock(self, node: CheckedModifiedBlock) -> None:
        from guppylang_internals.compiler.modifier_compiler import (
            compile_modified_block,
        )

        compile_modified_block(node, self.dfg, self.ctx, self.expr_compiler)
