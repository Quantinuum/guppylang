"""Linearity checking

Linearity checking across control-flow is done by the `CFGChecker`.
"""

import ast
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple, TypeGuard

from guppylang_internals.ast_util import AstNode, find_nodes, get_type
from guppylang_internals.cfg.analysis import LivenessAnalysis, LivenessDomain
from guppylang_internals.cfg.bb import BB, VariableStats
from guppylang_internals.checker.cfg_checker import (
    CheckedBB,
    CheckedCFG,
    Row,
    Signature,
)
from guppylang_internals.checker.core import (
    FieldAccess,
    Globals,
    Locals,
    Place,
    PlaceId,
    SubscriptAccess,
    TupleAccess,
    Variable,
    contains_subscript,
)
from guppylang_internals.checker.errors.linearity import (
    AlreadyUsedError,
    BorrowShadowedError,
    BorrowSubPlaceUsedError,
    ComprAlreadyUsedError,
    DropAfterCallError,
    MoveOutOfSubscriptError,
    NonCopyableCaptureError,
    NonCopyablePartialApplyError,
    NotOwnedError,
    PlaceNotUsedError,
    UnnamedExprNotUsedError,
    UnnamedFieldNotUsedError,
    UnnamedSubscriptNotUsedError,
    UnnamedTupleNotUsedError,
)
from guppylang_internals.definition.custom import CustomFunctionDef
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.error import GuppyError, GuppyTypeError
from guppylang_internals.nodes import (
    AnyCall,
    BarrierExpr,
    CheckedModifiedBlock,
    CheckedNestedFunctionDef,
    DesugaredArrayComp,
    DesugaredGenerator,
    DesugaredListComp,
    FieldAccessAndDrop,
    GlobalCall,
    InoutReturnSentinel,
    LocalCall,
    PartialApply,
    PlaceNode,
    StateResultExpr,
    SubscriptAccessAndDrop,
    TensorCall,
    TupleAccessAndDrop,
)
from guppylang_internals.tys.builtin import get_element_type, is_array_type
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    StructType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang_internals.diagnostic import Error


class UseKind(Enum):
    """The different ways places can be used."""

    #: A classical value is copied
    COPY = auto()

    #: A value is borrowed when passing it to a function
    BORROW = auto()

    #: Ownership of an owned value is transferred by passing it to a function
    CONSUME = auto()

    #: Ownership of an owned value is transferred by returning it
    RETURN = auto()

    #: An owned value is renamed or stored in a tuple/list
    MOVE = auto()

    @property
    def indicative(self) -> str:
        """Describes a use in an indicative mood.

        For example: "You cannot *consume* this qubit."
        """
        return self.name.lower()

    @property
    def subjunctive(self) -> str:
        """Describes a use in a subjunctive mood.

        For example: "This qubit cannot be *consumed*"
        """
        match self:
            case UseKind.COPY:
                return "copied"
            case UseKind.BORROW:
                return "borrowed"
            case UseKind.CONSUME:
                return "consumed"
            case UseKind.RETURN:
                return "returned"
            case UseKind.MOVE:
                return "moved"


class Use(NamedTuple):
    """Records data associated with a use of a place."""

    #: The AST node corresponding to the use
    node: AstNode

    #: The kind of use, i.e. is the value consumed, borrowed, returned, ...?
    kind: UseKind


class Scope(Locals[PlaceId, Place]):
    """Scoped collection of assigned places indexed by their id.

    Keeps track of which places have already been used.
    """

    parent_scope: "Scope | None"
    used_local: dict[PlaceId, Use]
    used_parent: dict[PlaceId, Use]

    def __init__(self, parent: "Scope | None" = None):
        self.used_local = {}
        self.used_parent = {}
        super().__init__({}, parent)

    def used(self, x: PlaceId) -> Use | None:
        """Checks whether a place has already been used."""
        if x in self.vars:
            return self.used_local.get(x, None)
        assert self.parent_scope is not None
        return self.parent_scope.used(x)

    def use(self, x: PlaceId, node: AstNode, kind: UseKind) -> None:
        """Records a use of a place.

        Works for places in the current scope as well as places in any parent scope.
        """
        if x in self.vars:
            self.used_local[x] = Use(node, kind)
        else:
            assert self.parent_scope is not None
            assert x in self.parent_scope
            self.used_parent[x] = Use(node, kind)
            self.parent_scope.use(x, node, kind)

    def assign(self, place: Place) -> None:
        """Records an assignment of a place."""
        assert place.defined_at is not None
        x = place.id
        self.vars[x] = place
        if x in self.used_local:
            self.used_local.pop(x)

    def stats(self) -> VariableStats[PlaceId]:
        assigned = {}
        for x, place in self.vars.items():
            assert place.defined_at is not None
            assigned[x] = place.defined_at
        used = {x: use.node for x, use in self.used_parent.items()}
        return VariableStats(assigned, used)


class BBLinearityChecker(ast.NodeVisitor):
    """AST visitor that checks linearity for a single basic block."""

    scope: Scope
    stats: VariableStats[PlaceId]
    func_name: str
    func_inputs: dict[PlaceId, Variable]
    globals: Globals

    def check(
        self,
        bb: "CheckedBB[Variable]",
        is_entry: bool,
        func_name: str,
        func_inputs: dict[PlaceId, Variable],
        globals: Globals,
    ) -> Scope:
        # Manufacture a scope that holds all places that are live at the start
        # of this BB
        input_scope = Scope()
        for var in bb.sig.input_row:
            for place in leaf_places(var):
                input_scope.assign(place)
        self.func_name = func_name
        self.func_inputs = func_inputs
        self.globals = globals

        # Open up a new nested scope to check the BB contents. This way we can track
        # when we use variables from the outside vs ones assigned in this BB. The only
        # exception is the entry BB since function arguments should be treated as part
        # of the entry BB
        self.scope = input_scope if is_entry else Scope(input_scope)

        for stmt in bb.statements:
            self.visit(stmt)
        if bb.branch_pred:
            self.visit(bb.branch_pred)
        return self.scope

    @contextmanager
    def new_scope(self) -> Generator[Scope, None, None]:
        scope, new_scope = self.scope, Scope(self.scope)
        self.scope = new_scope
        yield new_scope
        self.scope = scope

    def visit_PlaceNode(
        self,
        node: PlaceNode,
        /,
        use_kind: UseKind = UseKind.MOVE,
        is_call_arg: AnyCall | None = None,
    ) -> None:
        # Usage of borrowed variables is generally forbidden. The only exception is
        # letting them be reborrowed by another function call. In that case, our
        # `_visit_call_args` helper will set `use_kind=UseKind.BORROW`.
        is_inout_arg = use_kind == UseKind.BORROW
        if is_inout_var(node.place) and not is_inout_arg:
            err: Error = NotOwnedError(
                node,
                node.place,
                use_kind,
                is_call_arg is not None,
                self._call_name(is_call_arg),
                self.func_name,
            )
            arg_span = self.func_inputs[node.place.root.id].defined_at
            err.add_sub_diagnostic(NotOwnedError.MakeOwned(arg_span))
            # If the argument is a classical array, we can also suggest copying it.
            if has_explicit_copy(node.place.ty):
                err.add_sub_diagnostic(NotOwnedError.MakeCopy(node))
            raise GuppyError(err)
        # Places involving subscripts are handled differently since we ignore everything
        # after the subscript for the purposes of linearity checking.
        if subscript := contains_subscript(node.place):
            # We have to check the item type to determine if we can move out of the
            # subscript.
            if not is_inout_arg and not subscript.ty.copyable:
                err = MoveOutOfSubscriptError(node, use_kind, subscript.parent)
                err.add_sub_diagnostic(MoveOutOfSubscriptError.Explanation(None))
                raise GuppyError(err)
            self.visit(subscript.item_expr)
            self.scope.assign(subscript.item)
            # Visiting the `__getitem__(place.parent, place.item)` call ensures that we
            # linearity-check the parent and element.
            assert subscript.getitem_call is not None
            self.visit(subscript.getitem_call)
        # For all other places, we record uses of all leaves
        else:
            for place in leaf_places(node.place):
                x = place.id
                if (prev_use := self.scope.used(x)) and not place.ty.copyable:
                    err = AlreadyUsedError(node, place, use_kind)
                    err.add_sub_diagnostic(
                        AlreadyUsedError.PrevUse(prev_use.node, prev_use.kind)
                    )
                    if has_explicit_copy(place.ty):
                        err.add_sub_diagnostic(AlreadyUsedError.MakeCopy(None))
                    raise GuppyError(err)
                self.scope.use(x, node, use_kind)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        self._check_assign_targets(node.targets)

        # Check that borrowed vars are not being shadowed. This would also be caught by
        # the dataflow analysis later, however we can give nicer error messages here.
        [target] = node.targets
        for tgt in find_nodes(lambda n: isinstance(n, PlaceNode), target):
            assert isinstance(tgt, PlaceNode)
            if tgt.place.id in self.func_inputs:
                entry_place = self.func_inputs[tgt.place.id]
                if is_inout_var(entry_place):
                    err = BorrowShadowedError(tgt.place.defined_at, entry_place)
                    err.add_sub_diagnostic(BorrowShadowedError.Rename(None))
                    raise GuppyError(err)

    def visit_Return(self, node: ast.Return) -> None:
        # Intercept returns of places, so we can set the appropriate `use_kind` to get
        # nicer error messages
        if isinstance(node.value, PlaceNode):
            self.visit_PlaceNode(node.value, use_kind=UseKind.RETURN)
        elif isinstance(node.value, ast.Tuple):
            for elt in node.value.elts:
                if isinstance(elt, PlaceNode):
                    self.visit_PlaceNode(elt, use_kind=UseKind.RETURN)
                else:
                    self.visit(elt)
        elif node.value:
            self.visit(node.value)

    def _visit_call_args(self, func_ty: FunctionType, call: AnyCall) -> None:
        """Helper function to check the arguments of a function call.

        Populates the `use_kind` kwarg of `visit_PlaceNode` in case some of the
        arguments are places.
        """
        # Track literal subscripts to detect duplicates within this call
        # Key: (parent_place_id, literal_index_value)
        # Value: (argument_node, use_kind)
        literal_subscripts: dict[tuple[PlaceId, int], tuple[AstNode, UseKind]] = {}

        for inp, arg in zip(func_ty.inputs, call.args, strict=True):
            # Check for duplicate literal subscripts BEFORE visiting
            if result := is_simple_literal_subscript(arg):
                subscript, literal_idx = result
                key = (subscript.parent.id, literal_idx)
                use_kind = (
                    UseKind.BORROW if InputFlags.Inout in inp.flags else UseKind.CONSUME
                )

                if key in literal_subscripts and not subscript.ty.copyable:
                    prev_arg, prev_use_kind = literal_subscripts[key]
                    err = AlreadyUsedError(arg, subscript, use_kind)
                    err.add_sub_diagnostic(
                        AlreadyUsedError.PrevUse(prev_arg, prev_use_kind)
                    )
                    if has_explicit_copy(subscript.ty):
                        err.add_sub_diagnostic(AlreadyUsedError.MakeCopy(None))
                    raise GuppyError(err)

                literal_subscripts[key] = (arg, use_kind)

            # Visit the argument normally
            if isinstance(arg, PlaceNode):
                use_kind = (
                    UseKind.BORROW if InputFlags.Inout in inp.flags else UseKind.CONSUME
                )
                self.visit_PlaceNode(arg, use_kind=use_kind, is_call_arg=call)
            else:
                self.visit(arg)

    def _reassign_inout_args(self, func_ty: FunctionType, call: AnyCall) -> None:
        """Helper function to reassign the borrowed arguments after a function call."""
        for inp, arg in zip(func_ty.inputs, call.args, strict=True):
            if InputFlags.Inout in inp.flags:
                match arg:
                    case PlaceNode(place=place):
                        self._reassign_single_inout_arg(place, place.defined_at or arg)
                    case arg if not inp.ty.droppable:
                        err = DropAfterCallError(arg, inp.ty, self._call_name(call))
                        err.add_sub_diagnostic(DropAfterCallError.Assign(None))
                        raise GuppyError(err)

    def _reassign_single_inout_arg(self, place: Place, node: AstNode) -> None:
        """Helper function to reassign a single borrowed argument after a function
        call."""
        # Places involving subscripts are given back by visiting the `__setitem__` call
        if subscript := contains_subscript(place):
            assert subscript.setitem_call is not None
            for leaf in leaf_places(subscript.setitem_call.value_var):
                self.scope.assign(leaf)
            self.visit(subscript.setitem_call.call)
            self._reassign_single_inout_arg(subscript.parent, node)
        else:
            for leaf in leaf_places(place):
                assert not isinstance(leaf, SubscriptAccess)
                leaf = leaf.replace_defined_at(node)
                self.scope.assign(leaf)

    def _call_name(self, node: AnyCall | None) -> str | None:
        """Tries to extract the name of a called function from a call AST node."""
        if isinstance(node, LocalCall):
            return node.func.id if isinstance(node.func, ast.Name) else None
        elif isinstance(node, GlobalCall):
            return DEF_STORE.raw_defs[node.def_id].name
        return None

    def visit_GlobalCall(self, node: GlobalCall) -> None:
        func = ENGINE.get_parsed(node.def_id)
        assert isinstance(func, CallableDef)
        if isinstance(func, CustomFunctionDef) and not func.has_signature:
            func_ty = FunctionType(
                [FuncInput(get_type(arg), InputFlags.NoFlags) for arg in node.args],
                get_type(node),
            )
        else:
            func_ty = func.ty.instantiate(node.type_args)
        self._visit_call_args(func_ty, node)
        self._reassign_inout_args(func_ty, node)

    def visit_LocalCall(self, node: LocalCall) -> None:
        func_ty = get_type(node.func)
        assert isinstance(func_ty, FunctionType)
        self.visit(node.func)
        self._visit_call_args(func_ty, node)
        self._reassign_inout_args(func_ty, node)

    def visit_TensorCall(self, node: TensorCall) -> None:
        for arg in node.args:
            self.visit(arg)
        self._reassign_inout_args(node.tensor_ty, node)

    def visit_PartialApply(self, node: PartialApply) -> None:
        self.visit(node.func)
        for arg in node.args:
            ty = get_type(arg)
            if not ty.copyable:
                err = NonCopyablePartialApplyError(node)
                err.add_sub_diagnostic(NonCopyablePartialApplyError.Captured(arg, ty))
                raise GuppyError(err)
            self.visit(arg)

    def visit_FieldAccessAndDrop(self, node: FieldAccessAndDrop) -> None:
        # A field access on a value that is not a place. This means the value can no
        # longer be accessed after the field has been projected out. Thus, this is only
        # legal if there are no remaining linear fields on the value
        self.visit(node.value)
        for field in node.struct_ty.fields:
            if field.name != node.field.name and not field.ty.droppable:
                err = UnnamedFieldNotUsedError(node.value, field, node.struct_ty)
                err.add_sub_diagnostic(UnnamedFieldNotUsedError.Fix(None, node.field))
                raise GuppyError(err)

    def visit_SubscriptAccessAndDrop(self, node: SubscriptAccessAndDrop) -> None:
        # A subscript access on a value that is not a place. This means the value can no
        # longer be accessed after the item has been projected out. Thus, this is only
        # legal if the items in the container are not linear
        elem_ty = get_type(node.getitem_expr)
        if not elem_ty.droppable:
            value = node.original_expr.value
            err = UnnamedSubscriptNotUsedError(value, get_type(value))
            err.add_sub_diagnostic(
                UnnamedSubscriptNotUsedError.SubscriptHint(node.item_expr)
            )
            err.add_sub_diagnostic(UnnamedSubscriptNotUsedError.Fix(None))
            raise GuppyTypeError(err)
        self.visit(node.item_expr)
        self.scope.assign(node.item)
        self.visit(node.getitem_expr)

    def visit_TupleAccessAndDrop(self, node: TupleAccessAndDrop) -> None:
        # A tuple access on a value that is not a place. This means the value can no
        # longer be accessed after the element has been projected out. Thus, this is
        # only legal if there are no remaining linear elements in the tuple
        self.visit(node.value)
        for idx, elem_ty in enumerate(node.tuple_ty.element_types):
            if idx != node.index and not elem_ty.droppable:
                err = UnnamedTupleNotUsedError(node.value, node.tuple_ty)
                err.add_sub_diagnostic(UnnamedTupleNotUsedError.Fix(None))
                raise GuppyError(err)

    def visit_BarrierExpr(self, node: BarrierExpr) -> None:
        self._visit_call_args(node.func_ty, node)
        self._reassign_inout_args(node.func_ty, node)

    def visit_StateResultExpr(self, node: StateResultExpr) -> None:
        self._visit_call_args(node.func_ty, node)
        self._reassign_inout_args(node.func_ty, node)

    def visit_Expr(self, node: ast.Expr) -> None:
        # An expression statement where the return value is discarded
        self.visit(node.value)
        ty = get_type(node.value)
        if not ty.droppable:
            err = UnnamedExprNotUsedError(node, ty)
            err.add_sub_diagnostic(UnnamedExprNotUsedError.Fix(None))
            raise GuppyTypeError(err)

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> None:
        self._check_comprehension(node.generators, node.elt)

    def visit_DesugaredArrayComp(self, node: DesugaredArrayComp) -> None:
        self._check_comprehension([node.generator], node.elt)

    def visit_CheckedNestedFunctionDef(self, node: CheckedNestedFunctionDef) -> None:
        # Linearity of the nested function has already been checked. We just need to
        # verify that no linear variables are captured
        # TODO: In the future, we could support capturing of non-linear subplaces
        for var, use in node.captured.values():
            if not var.ty.copyable:
                err = NonCopyableCaptureError(use, var)
                err.add_sub_diagnostic(
                    NonCopyableCaptureError.DefinedHere(var.defined_at)
                )
                raise GuppyError(err)
            for place in leaf_places(var):
                self.scope.use(place.id, use, UseKind.COPY)
        self.scope.assign(Variable(node.name, node.ty, node))

    def _check_assign_targets(self, targets: list[ast.expr]) -> None:
        """Helper function to check assignments."""
        # We're not allowed to override an unused linear place
        [target] = targets
        for tgt in find_nodes(lambda n: isinstance(n, PlaceNode), target):
            assert isinstance(tgt, PlaceNode)
            # Special error message for shadowing of borrowed vars
            x = tgt.place.id
            if x in self.scope.vars and is_inout_var(self.scope[x]):
                err: Error = BorrowShadowedError(tgt, tgt.place)
                err.add_sub_diagnostic(BorrowShadowedError.Rename(None))
                raise GuppyError(err)
            # Subscript assignments also require checking the `__setitem__` call
            if subscript := contains_subscript(tgt.place):
                assert subscript.setitem_call is not None
                self.visit(subscript.item_expr)
                self.scope.assign(subscript.item)
                self.scope.assign(subscript.setitem_call.value_var)
                self.visit(subscript.setitem_call.call)
            else:
                for tgt_place in leaf_places(tgt.place):
                    x = tgt_place.id
                    # Only check for overrides of places locally defined in this BB.
                    # Global checks are handled by dataflow analysis.
                    if x in self.scope.vars and x not in self.scope.used_local:
                        place = self.scope[x]
                        if not place.ty.droppable:
                            err = PlaceNotUsedError(place.defined_at, place)
                            err.add_sub_diagnostic(PlaceNotUsedError.Fix(None))
                            raise GuppyError(err)
                    self.scope.assign(tgt_place)

    def _check_comprehension(
        self, gens: list[DesugaredGenerator], elt: ast.expr
    ) -> None:
        """Helper function to recursively check list comprehensions."""
        if not gens:
            self.visit(elt)
            return

        # Check the iterator expression in the current scope
        gen, *gens = gens
        self.visit(gen.iter_assign.value)
        assert isinstance(gen.iter, PlaceNode)

        # The rest is checked in a new nested scope so we can track which variables
        # are introduced and used inside the loop
        with self.new_scope() as inner_scope:
            # In particular, assign the iterator variable in the new scope
            self._check_assign_targets(gen.iter_assign.targets)
            self.visit(gen.next_call)
            self._check_assign_targets([gen.target])
            self._check_assign_targets(gen.iter_assign.targets)

            # `if` guards are generally not allowed when we're iterating over linear
            # variables. The only exception is if all linear variables are already
            # consumed by the first guard
            if gen.ifs:
                first_if, *other_ifs = gen.ifs
                # Check if there are linear iteration variables that have not been used
                # by the first guard
                self.visit(first_if)
                for place in self.scope.vars.values():
                    # The only exception is the iterator variable since we make sure
                    # that it is carried through each iteration during Hugr generation
                    if place == gen.iter.place:
                        continue
                    for leaf in leaf_places(place):
                        x = leaf.id
                        # Also ignore borrowed variables
                        if x in inner_scope.used_parent and (
                            inner_scope.used_parent[x].kind == UseKind.BORROW
                        ):
                            continue
                        if not self.scope.used(x) and not place.ty.droppable:
                            err = PlaceNotUsedError(place.defined_at, place)
                            err.add_sub_diagnostic(
                                PlaceNotUsedError.Branch(first_if, False)
                            )
                            raise GuppyTypeError(err)
                for expr in other_ifs:
                    self.visit(expr)

            # Recursively check the remaining generators
            self._check_comprehension(gens, elt)

            # Look for any variables that are used from the outer scope. This is so we
            # can feed them through the loop. Note that we could also use non-local
            # edges, but we can't handle them in lower parts of the stack yet :/
            # TODO: Reinstate use of non-local edges.
            #  See https://github.com/quantinuum/guppylang/issues/963
            gen.used_outer_places = []
            for x, use in inner_scope.used_parent.items():
                place = inner_scope[x]
                gen.used_outer_places.append(place)
                if use.kind == UseKind.BORROW:
                    # Since `x` was borrowed, we know that is now also assigned in the
                    # inner scope since it gets reassigned in the local scope after the
                    # borrow expires.
                    # Also mark this place as implicitly used so we don't complain about
                    # it later.
                    for leaf in leaf_places(place):
                        inner_scope.use(
                            leaf.id, InoutReturnSentinel(leaf), UseKind.RETURN
                        )

            # Mark the iterator as used since it's carried into the next iteration
            for leaf in leaf_places(gen.iter.place):
                self.scope.use(leaf.id, gen.iter, UseKind.CONSUME)

            # We have to make sure that all linear variables that were introduced in the
            # inner scope have been used
            for place in inner_scope.vars.values():
                for leaf in leaf_places(place):
                    x = leaf.id
                    if not leaf.ty.droppable and not inner_scope.used(x):
                        raise GuppyTypeError(PlaceNotUsedError(leaf.defined_at, leaf))

        # On the other hand, we have to ensure that no linear places from the
        # outer scope have been used inside the comprehension (they would be used
        # multiple times since the comprehension body is executed repeatedly)
        for x, use in inner_scope.used_parent.items():
            place = inner_scope[x]
            # The only exception are values that are only borrowed from the outer
            # scope. These can be safely reassigned.
            if use.kind == UseKind.BORROW:
                self._reassign_single_inout_arg(place, use.node)
            elif not place.ty.copyable:
                raise GuppyTypeError(ComprAlreadyUsedError(use.node, place, use.kind))

    def visit_CheckedModifiedBlock(self, node: CheckedModifiedBlock) -> None:
        # Linear usage of variables in a with statement
        # ```
        # with control(c1, c2, ...):
        #   body(q1, q2, ...) # captured variables
        # ````
        # is the same as to assume that this is a function call
        # `WithCtrl(q1, q2, ..., c1, c2, ...)`
        # where `WithCtrl` is a function that takes the control as mutable references.
        # Therefore, we apply the same linearity rules as for function arguments.
        # ```
        # def WithCtrl(q1, q2, ..., c1, c2, ...):
        #   body(q1, q2, ...)
        # ```

        # check control
        for ctrl in node.control:
            for arg in ctrl.ctrl:
                if isinstance(arg, PlaceNode):
                    self.visit_PlaceNode(arg, use_kind=UseKind.BORROW, is_call_arg=None)
                else:
                    ty = get_type(arg)
                    unnamed_err = UnnamedExprNotUsedError(arg, ty)
                    unnamed_err.add_sub_diagnostic(UnnamedExprNotUsedError.Fix(None))
                    raise GuppyTypeError(unnamed_err)

        # check power
        for power in node.power:
            if isinstance(power.iter, PlaceNode):
                self.visit_PlaceNode(
                    power.iter, use_kind=UseKind.CONSUME, is_call_arg=None
                )
            else:
                self.visit(power.iter)

        # check captured variables
        for var, use in node.captured.values():
            for place in leaf_places(var):
                use_kind = (
                    UseKind.BORROW if InputFlags.Inout in var.flags else UseKind.CONSUME
                )

                x = place.id
                if (prev_use := self.scope.used(x)) and not place.ty.copyable:
                    used_err = AlreadyUsedError(use, place, use_kind)
                    used_err.add_sub_diagnostic(
                        AlreadyUsedError.PrevUse(prev_use.node, prev_use.kind)
                    )
                    if has_explicit_copy(place.ty):
                        used_err.add_sub_diagnostic(AlreadyUsedError.MakeCopy(None))
                    raise GuppyError(used_err)
                self.scope.use(x, node, use_kind)

        # reassign controls
        for ctrl in node.control:
            for arg in ctrl.ctrl:
                assert isinstance(arg, PlaceNode)  # Checked above
                self._reassign_single_inout_arg(arg.place, arg.place.defined_at or arg)

        # reassign captured variables
        for var, use in node.captured.values():
            if InputFlags.Inout in var.flags:
                self._reassign_single_inout_arg(var, var.defined_at or use)


def leaf_places(place: Place) -> Iterator[Place]:
    """Returns all leaf descendant projections of a place."""
    stack = [place]
    while stack:
        place = stack.pop()
        if isinstance(place.ty, StructType):
            stack += [
                FieldAccess(place, field, place.defined_at) for field in place.ty.fields
            ]
        elif isinstance(place.ty, TupleType):
            stack += [
                TupleAccess(place, elem_ty, idx, None)
                for idx, elem_ty in enumerate(place.ty.element_types)
            ]
        else:
            yield place


def is_inout_var(place: Place) -> TypeGuard[Variable]:
    """Checks whether a place is a borrowed variable."""
    return isinstance(place, Variable) and InputFlags.Inout in place.flags


def has_explicit_copy(ty: Type) -> bool:
    """Checks whether a type has an explicit copy function.

    Currently, this is only the case for arrays with copyable elements."""
    if not is_array_type(ty):
        return False
    return get_element_type(ty).copyable


def get_literal_index(subscript: SubscriptAccess) -> int | None:
    """Extracts the literal index value from a subscript access.

    Returns the integer index if item_expr is ast.Constant, otherwise None.
    This allows us to detect duplicate literal subscripts at compile time.
    """
    if isinstance(subscript.item_expr, ast.Constant):
        value = subscript.item_expr.value
        if isinstance(value, int):
            return value
    return None


def is_simple_literal_subscript(
    arg: ast.expr,
) -> tuple[SubscriptAccess, int] | None:
    """Checks if an argument is a simple literal subscript access.

    A simple literal subscript is one where:
    - The argument is a PlaceNode
    - It contains a subscript access
    - The subscript's parent is a Variable (not nested subscripts)
    - There are no projections after the subscript (e.g., field accesses)
    - The index is a literal constant (not a variable)

    Returns a tuple of (subscript, literal_index) if all conditions are met,
    otherwise None.

    This conservative check avoids false positives for:
    - Nested subscripts: qs[0][0] vs qs[0][1] (different inner indices)
    - Field accesses: ss[0].q1 vs ss[0].q2 (different fields)
    - Dynamic indices: array[i] where i is a variable
    """
    if not isinstance(arg, PlaceNode):
        return None

    subscript = contains_subscript(arg.place)
    if not subscript:
        return None

    # Check parent is a Variable (not nested subscripts)
    if not isinstance(subscript.parent, Variable):
        return None

    # Check no projections after subscript (e.g., field access)
    if subscript != arg.place:
        return None

    # Check for literal index
    literal_idx = get_literal_index(subscript)
    if literal_idx is None:
        return None

    return (subscript, literal_idx)


def check_cfg_linearity(
    cfg: "CheckedCFG[Variable]", func_name: str, globals: Globals
) -> "CheckedCFG[Place]":
    """Checks whether a CFG satisfies the linearity requirements.

    Raises a user-error if linearity violations are found.

    Returns a new CFG with refined basic block signatures in terms of *places* rather
    than just variables.
    """
    bb_checker = BBLinearityChecker()
    func_inputs: dict[PlaceId, Variable] = {v.id: v for v in cfg.entry_bb.sig.input_row}
    scopes: dict[BB, Scope] = {
        bb: bb_checker.check(
            bb,
            is_entry=bb == cfg.entry_bb,
            func_name=func_name,
            func_inputs=func_inputs,
            globals=globals,
        )
        for bb in cfg.bbs
    }

    # Mark the borrowed variables as implicitly used in the exit BB
    exit_scope = scopes[cfg.exit_bb]
    for var in cfg.entry_bb.sig.input_row:
        if InputFlags.Inout in var.flags:
            for leaf in leaf_places(var):
                exit_scope.use(leaf.id, InoutReturnSentinel(var=var), UseKind.RETURN)

    # Edge case: If the exit is unreachable, then the function will never terminate, so
    # there is no need to give the borrowed values back to the caller. To ensure that
    # the generated Hugr is still valid, we have to thread the borrowed arguments
    # through the non-terminating loop. We achieve this by considering borrowed
    # variables as live in every BB, even if the actual use in the exit is unreachable.
    # This is done by including borrowed vars in the initial value for the liveness
    # analysis below. The analogous thing was also done in the previous `CFG.analyze`
    # pass.
    live_default: LivenessDomain[PlaceId] = (
        {
            leaf.id: cfg.exit_bb
            for var in cfg.entry_bb.sig.input_row
            if InputFlags.Inout in var.flags
            for leaf in leaf_places(var)
        }
        if not cfg.exit_bb.reachable
        else {}
    )

    # Run liveness analysis with this initial value
    stats = {bb: scope.stats() for bb, scope in scopes.items()}
    live_before = LivenessAnalysis(
        stats, initial=live_default, include_unreachable=False
    ).run(cfg.bbs)

    # Construct a CFG that tracks places instead of just variables
    result_cfg: CheckedCFG[Place] = CheckedCFG(cfg.input_tys, cfg.output_ty)
    checked: dict[BB, CheckedBB[Place]] = {}

    for bb, scope in scopes.items():
        live_before_bb = live_before[bb]

        # We have to check that used not copyable variables are not being outputted
        for succ in bb.successors:
            live = live_before[succ]
            for x, use_bb in live.items():
                use_scope = scopes[use_bb]
                place = use_scope[x]
                if not place.ty.copyable and (prev_use := scope.used(x)):
                    use = use_scope.used_parent[x]
                    # Special case if this is a use arising from the implicit returning
                    # of a borrowed argument
                    if isinstance(use.node, InoutReturnSentinel):
                        assert isinstance(use.node.var, Variable)
                        assert InputFlags.Inout in use.node.var.flags
                        err: Error = BorrowSubPlaceUsedError(
                            use.node.var.defined_at, use.node.var, place
                        )
                        err.add_sub_diagnostic(
                            BorrowSubPlaceUsedError.PrevUse(
                                prev_use.node, prev_use.kind
                            )
                        )
                        err.add_sub_diagnostic(BorrowSubPlaceUsedError.Fix(None))
                        raise GuppyError(err)
                    err = AlreadyUsedError(use.node, place, use.kind)
                    err.add_sub_diagnostic(
                        AlreadyUsedError.PrevUse(prev_use.node, prev_use.kind)
                    )
                    if has_explicit_copy(place.ty):
                        err.add_sub_diagnostic(AlreadyUsedError.MakeCopy(None))
                    raise GuppyError(err)

        # On the other hand, unused variables that are not droppable *must* be outputted
        for place in scope.values():
            for leaf in leaf_places(place):
                x = leaf.id
                # Some values are just in scope because the type checker determined
                # them as live in the first (less precises) dataflow analysis. It
                # might be the case that x is actually not live when considering
                # the second, more fine-grained, analysis based on places.
                if x not in live_before_bb and x not in scope.vars:
                    continue
                used_later = all(x in live_before[succ] for succ in bb.successors)
                if not leaf.ty.droppable and not scope.used(x) and not used_later:
                    err = PlaceNotUsedError(scope[x].defined_at, leaf)
                    # If the variable is consumed (not just borrowed) on some
                    # paths, highlight the branch that leads to the leak.
                    consumed_succs = set()
                    for succ in bb.successors:
                        if x not in live_before[succ]:
                            continue
                        use_bb = live_before[succ][x]
                        if x in scopes[use_bb].used_parent:
                            use = scopes[use_bb].used_parent[x]
                            if use.kind not in (UseKind.BORROW, UseKind.COPY):
                                consumed_succs.add(succ)
                    if consumed_succs:
                        assert bb.branch_pred is not None
                        [left_succ, _] = bb.successors
                        err.add_sub_diagnostic(
                            PlaceNotUsedError.Branch(
                                bb.branch_pred,
                                left_succ in consumed_succs,
                            )
                        )
                    err.add_sub_diagnostic(PlaceNotUsedError.Fix(None))
                    raise GuppyError(err)

        def live_places_row(
            bb: BB, original_row: Row[Variable], pred_scope: Scope | None
        ) -> Row[Place]:
            """Construct a row of all places that are live at the start of a given BB.

            The only exception are input and exit BBs whose signature should not be
            split up into places but instead keep the original variable signature.
            """
            if bb in (cfg.entry_bb, cfg.exit_bb):
                return original_row
            assert pred_scope is not None
            return [pred_scope[x] for x in live_before[bb]]

        assert isinstance(bb, CheckedBB)
        sig = Signature(
            input_row=live_places_row(bb, bb.sig.input_row, scope.parent_scope),
            output_rows=[
                live_places_row(succ, output_row, scope)
                for succ, output_row in zip(
                    bb.successors, bb.sig.output_rows, strict=True
                )
            ],
        )
        checked[bb] = CheckedBB(
            bb.idx,
            result_cfg,
            bb.statements,
            branch_pred=bb.branch_pred,
            reachable=bb.reachable,
            sig=sig,
        )

    # Fill in missing fields of the result CFG
    result_cfg.bbs = list(checked.values())
    result_cfg.entry_bb = checked[cfg.entry_bb]
    result_cfg.exit_bb = checked[cfg.exit_bb]
    result_cfg.live_before = {checked[bb]: cfg.live_before[bb] for bb in cfg.bbs}
    result_cfg.ass_before = {checked[bb]: cfg.ass_before[bb] for bb in cfg.bbs}
    result_cfg.maybe_ass_before = {
        checked[bb]: cfg.maybe_ass_before[bb] for bb in cfg.bbs
    }
    result_cfg.unitary_flags = cfg.unitary_flags
    for bb in cfg.bbs:
        checked[bb].predecessors = [checked[pred] for pred in bb.predecessors]
        checked[bb].successors = [checked[succ] for succ in bb.successors]
    return result_cfg
