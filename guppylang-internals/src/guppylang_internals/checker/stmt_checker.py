"""Type checking code for statements.

Operates on statements in a basic block after CFG construction. In particular, we
assume that statements involving control flow (i.e. if, while, break, and return
statements) have been removed during CFG construction.

After checking, we return a desugared statement where all sub-expression have been type
annotated.
"""

import ast
import functools
from collections.abc import Iterable, Sequence
from dataclasses import replace
from itertools import takewhile
from typing import TypeVar, cast

from guppylang_internals.ast_util import (
    AstVisitor,
    get_type,
    with_loc,
    with_type,
)
from guppylang_internals.cfg.bb import BB, BBStatement
from guppylang_internals.cfg.builder import (
    desugar_comprehension,
    make_var,
    tmp_vars,
)
from guppylang_internals.checker.core import (
    Context,
    FieldAccess,
    SubscriptAccess,
    Variable,
)
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.checker.errors.type_errors import (
    AssignFieldTypeMismatchError,
    AssignNonPlaceHelp,
    AssignSubscriptTypeMismatchError,
    AttributeNotFoundError,
    MissingReturnValueError,
    StarredTupleUnpackError,
    TypeInferenceError,
    TypeMismatchError,
    UnpackableError,
    WrongNumberOfArgsError,
    WrongNumberOfUnpacksError,
)
from guppylang_internals.checker.expr_checker import (
    ExprChecker,
    ExprSynthesizer,
    check_place_assignable,
    synthesize_comprehension,
)
from guppylang_internals.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang_internals.nodes import (
    AnyUnpack,
    ArrayUnpack,
    DesugaredArrayComp,
    IterableUnpack,
    MakeIter,
    ModifiedBlock,
    NestedFunctionDef,
    PlaceNode,
    TupleUnpack,
    UnpackPattern,
)
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys.builtin import (
    array_type,
    get_array_length,
    get_element_type,
    get_iter_size,
    is_array_type,
    is_sized_iter_type,
    nat_type,
)
from guppylang_internals.tys.const import ConstValue, ExistentialConstVar
from guppylang_internals.tys.parsing import type_from_ast
from guppylang_internals.tys.qubit import is_qubit_ty, qubit_ty
from guppylang_internals.tys.subst import Subst
from guppylang_internals.tys.ty import (
    ExistentialTypeVar,
    FunctionType,
    NoneType,
    NumericType,
    StructType,
    TupleType,
    Type,
)


class StmtChecker(AstVisitor[BBStatement]):
    ctx: Context
    bb: BB | None
    return_ty: Type | None

    def __init__(
        self, ctx: Context, bb: BB | None = None, return_ty: Type | None = None
    ) -> None:
        assert not return_ty or not return_ty.unsolved_vars
        self.ctx = ctx
        self.bb = bb
        self.return_ty = return_ty

    def check_stmts(self, stmts: Sequence[BBStatement]) -> list[BBStatement]:
        return [self.visit(s) for s in stmts]

    def _synth_expr(self, node: ast.expr) -> tuple[ast.expr, Type]:
        return ExprSynthesizer(self.ctx).synthesize(node)

    def _synth_instance_fun(
        self,
        node: ast.expr,
        args: list[ast.expr],
        func_name: str,
        description: str,
        exp_sig: FunctionType | None = None,
        give_reason: bool = False,
    ) -> tuple[ast.expr, Type]:
        return ExprSynthesizer(self.ctx).synthesize_instance_func(
            node, args, func_name, description, exp_sig, give_reason
        )

    def _check_expr(
        self, node: ast.expr, ty: Type, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
        return ExprChecker(self.ctx).check(node, ty, kind)

    @functools.singledispatchmethod
    def _check_assign(self, lhs: ast.expr, rhs: ast.expr, rhs_ty: Type) -> ast.expr:
        """Helper function to check assignments with patterns."""
        raise InternalGuppyError("Unexpected assignment pattern")

    @_check_assign.register
    def _check_variable_assign(
        self, lhs: ast.Name, _rhs: ast.expr, rhs_ty: Type
    ) -> PlaceNode:
        x = lhs.id
        var = Variable(x, rhs_ty, lhs)
        self.ctx.locals[x] = var
        return with_loc(lhs, with_type(rhs_ty, PlaceNode(place=var)))

    @_check_assign.register
    def _check_field_assign(
        self, lhs: ast.Attribute, _rhs: ast.expr, rhs_ty: Type
    ) -> PlaceNode:
        # Unfortunately, the `attr` is just a string,  not an AST node, so we
        # have to compute its span by hand. This is fine since linebreaks are
        # not allowed in the identifier following the `.`
        span = to_span(lhs)
        value, attr = lhs.value, lhs.attr
        attr_span = Span(span.end.shift_left(len(attr)), span.end)
        value, struct_ty = self._synth_expr(value)
        if not isinstance(struct_ty, StructType) or attr not in struct_ty.field_dict:
            raise GuppyTypeError(AttributeNotFoundError(attr_span, struct_ty, attr))
        field = struct_ty.field_dict[attr]
        # TODO: In the future, we could infer some type args here
        if field.ty != rhs_ty:
            # TODO: Get hold of a span for the RHS and use a regular `TypeMismatchError`
            #  instead (maybe with a custom hint).
            raise GuppyTypeError(AssignFieldTypeMismatchError(attr_span, rhs_ty, field))
        if not isinstance(value, PlaceNode):
            # For now we complain if someone tries to assign to something that is not a
            # place, e.g. `f().a = 4`. This would only make sense if there is another
            # reference to the return value of `f`, otherwise the mutation cannot be
            # observed. We can start supporting this once we have proper reference
            # semantics.
            err = UnsupportedError(value, "Assigning to this expression", singular=True)
            err.add_sub_diagnostic(AssignNonPlaceHelp(None, field))
            raise GuppyError(err)
        if field.ty.copyable:
            raise GuppyError(
                UnsupportedError(
                    attr_span, "Mutation of classical fields", singular=True
                )
            )
        place = FieldAccess(value.place, struct_ty.field_dict[attr], lhs)
        place = check_place_assignable(place, self.ctx, lhs, "assignable")
        return with_loc(lhs, with_type(rhs_ty, PlaceNode(place=place)))

    @_check_assign.register
    def _check_subscript_assign(
        self, lhs: ast.Subscript, rhs: ast.expr, rhs_ty: Type
    ) -> PlaceNode:
        # Check subscript is array subscript.
        value, container_ty = self._synth_expr(lhs.value)
        if not is_array_type(container_ty):
            raise GuppyError(
                UnsupportedError(lhs, "Subscript assignments to non-arrays")
            )

        # Check array element type matches type of RHS.
        element_ty = get_element_type(container_ty)
        if element_ty != rhs_ty:
            raise GuppyTypeError(
                AssignSubscriptTypeMismatchError(to_span(lhs), rhs_ty, element_ty)
            )

        # As with field assignment, only allow place assignments for now.
        if not isinstance(value, PlaceNode):
            raise GuppyError(
                UnsupportedError(value, "Assigning to this expression", singular=True)
            )

        # Create a subscript place
        item_expr, item_ty = self._synth_expr(lhs.slice)
        item = Variable(next(tmp_vars), item_ty, item_expr)
        place = SubscriptAccess(value.place, item, rhs_ty, item_expr)

        # Calling `check_place_assignable` makes sure that `__setitem__` is implemented
        place = check_place_assignable(place, self.ctx, lhs, "assignable")
        return with_loc(lhs, with_type(rhs_ty, PlaceNode(place=place)))

    @_check_assign.register
    def _check_tuple_assign(
        self, lhs: ast.Tuple, rhs: ast.expr, rhs_ty: Type
    ) -> AnyUnpack:
        return self._check_unpack_assign(lhs, rhs, rhs_ty)

    @_check_assign.register
    def _check_list_assign(
        self, lhs: ast.List, rhs: ast.expr, rhs_ty: Type
    ) -> AnyUnpack:
        return self._check_unpack_assign(lhs, rhs, rhs_ty)

    def _check_unpack_assign(
        self, lhs: ast.Tuple | ast.List, rhs: ast.expr, rhs_ty: Type
    ) -> AnyUnpack:
        """Helper function to check unpacking assignments.

        These are the ones where the LHS is either a tuple or a list.
        """
        # Parse LHS into `left, *starred, right`
        pattern = parse_unpack_pattern(lhs)
        left, starred, right = pattern.left, pattern.starred, pattern.right
        # Check that the RHS has an appropriate type to be unpacked
        unpack, rhs_elts, rhs_tys = self._check_unpackable(rhs, rhs_ty, pattern)

        # Check that the numbers match up on the LHS and RHS
        num_lhs, num_rhs = len(right) + len(left), len(rhs_tys)
        err = WrongNumberOfUnpacksError(
            lhs, num_rhs, num_lhs, at_least=starred is not None
        )
        if num_lhs > num_rhs:
            # Build span that covers the unexpected elts on the LHS
            span = Span(to_span(lhs.elts[num_rhs]).start, to_span(lhs.elts[-1]).end)
            raise GuppyTypeError(replace(err, span=span))
        elif num_lhs < num_rhs and not starred:
            raise GuppyTypeError(err)

        # Recursively check any nested patterns on the left or right
        le, rs = len(left), len(rhs_elts) - len(right)  # left_end, right_start
        unpack.pattern.left = [
            self._check_assign(pat, elt, ty)
            for pat, elt, ty in zip(left, rhs_elts[:le], rhs_tys[:le], strict=True)
        ]
        unpack.pattern.right = [
            self._check_assign(pat, elt, ty)
            for pat, elt, ty in zip(right, rhs_elts[rs:], rhs_tys[rs:], strict=True)
        ]

        # Starred assignments are collected into an array
        if starred:
            starred_tys = rhs_tys[le:rs]
            assert all_equal(starred_tys)
            if starred_tys:
                starred_ty, *_ = starred_tys
            # Starred part could be empty. If it's an array or iterable unpack, we're
            # still fine since we know the yielded type
            elif isinstance(unpack, ArrayUnpack):
                starred_ty = unpack.elt_type
            elif isinstance(unpack, IterableUnpack):
                starred_ty = unpack.compr.elt_ty
            # For tuple unpacks, there is no way to infer a type for the empty starred
            # part
            else:
                unsolved = array_type(ExistentialTypeVar.fresh("T", True, True), 0)
                raise GuppyError(TypeInferenceError(starred, unsolved))
            array_ty = array_type(starred_ty, len(starred_tys))
            unpack.pattern.starred = self._check_assign(starred, rhs_elts[0], array_ty)

        return with_type(rhs_ty, with_loc(lhs, unpack))

    def _check_unpackable(
        self, expr: ast.expr, ty: Type, pattern: UnpackPattern
    ) -> tuple[AnyUnpack, list[ast.expr], Sequence[Type]]:
        """Checks that the given expression can be used in an unpacking assignment.

        This is the case for expressions with tuple types or ones that are iterable with
        a static size. Also checks that the expression is compatible with the given
        unpacking pattern.

        Returns an AST node capturing the unpacking operation together with expressions
        and types for all unpacked items. Emits a user error if the given expression is
        not unpackable.
        """
        left, starred, right = pattern.left, pattern.starred, pattern.right
        if isinstance(ty, TupleType):
            # Starred assignment of tuples is only allowed if all starred elements have
            # the same type
            if starred:
                starred_tys = (
                    ty.element_types[len(left) : -len(right)]
                    if right
                    else ty.element_types[len(left) :]
                )
                if not all_equal(starred_tys):
                    tuple_ty = TupleType(starred_tys)
                    raise GuppyError(StarredTupleUnpackError(starred, tuple_ty))
            tys = ty.element_types
            elts = expr.elts if isinstance(expr, ast.Tuple) else [expr] * len(tys)
            return TupleUnpack(pattern), elts, tys

        elif is_array_type(ty):
            match get_array_length(ty):
                case ConstValue(value=int(size)):
                    elt_ty = get_element_type(ty)
                    unpack = ArrayUnpack(pattern, size, elt_ty)
                    return unpack, size * [expr], size * [elt_ty]
                case generic_size:
                    err = UnpackableError(expr, get_type(expr))
                    err.add_sub_diagnostic(
                        UnpackableError.GenericSize(None, generic_size)
                    )
                    raise GuppyError(err)

        elif self.ctx.globals.get_instance_func(ty, "__iter__"):
            size = check_iter_unpack_has_static_size(expr, self.ctx)
            # Create a dummy variable and assign the expression to it. This helps us to
            # wire it up correctly during Hugr generation.
            var = self._check_assign(make_var(next(tmp_vars), expr), expr, ty)
            assert isinstance(var, PlaceNode)
            # We collect the whole RHS into an array. For this, we can reuse the
            # existing array comprehension logic.
            elt = make_var(next(tmp_vars), expr)
            gen = ast.comprehension(target=elt, iter=var, ifs=[], is_async=False)
            [gen], elt = desugar_comprehension([with_loc(expr, gen)], elt, expr)
            # Type check the comprehension
            [gen], elt, elt_ty = synthesize_comprehension(expr, [gen], elt, self.ctx)
            compr = DesugaredArrayComp(
                elt, gen, length=ConstValue(nat_type(), size), elt_ty=elt_ty
            )
            compr = with_type(array_type(elt_ty, size), compr)
            return IterableUnpack(pattern, compr, var), size * [elt], size * [elt_ty]

        # Otherwise, we can't unpack this expression
        raise GuppyError(UnpackableError(expr, ty))

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        if len(node.targets) > 1:
            # This is the case for assignments like `a = b = 1`
            raise GuppyError(UnsupportedError(node, "Multi assignments"))

        [target] = node.targets
        node.value, ty = self._synth_expr(node.value)
        node.targets = [self._check_assign(target, node.value, ty)]
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.stmt:
        if node.value is None:
            raise GuppyError(UnsupportedError(node, "Variable declarations"))
        ty = type_from_ast(node.annotation, self.ctx.parsing_ctx)
        node.value, subst = self._check_expr(node.value, ty)
        assert not ty.unsolved_vars  # `ty` must be closed!
        assert len(subst) == 0
        target = self._check_assign(node.target, node.value, ty)
        return with_loc(node, ast.Assign(targets=[target], value=node.value))

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.stmt:
        bin_op = with_loc(
            node, ast.BinOp(left=node.target, op=node.op, right=node.value)
        )
        assign = with_loc(node, ast.Assign(targets=[node.target], value=bin_op))
        return self.visit_Assign(assign)

    def visit_Expr(self, node: ast.Expr) -> ast.stmt:
        # An expression statement where the return value is discarded
        node.value, _ = self._synth_expr(node.value)
        return node

    def visit_Return(self, node: ast.Return) -> ast.stmt:
        if not self.return_ty:
            raise InternalGuppyError("return_ty required to check return stmt!")

        if node.value is not None:
            node.value, subst = self._check_expr(
                node.value, self.return_ty, "return value"
            )
            assert len(subst) == 0  # `self.return_ty` is closed!
        elif not isinstance(self.return_ty, NoneType):
            raise GuppyTypeError(MissingReturnValueError(node, self.return_ty))
        return node

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> ast.stmt:
        from guppylang_internals.checker.func_checker import check_nested_func_def

        if not self.bb:
            raise InternalGuppyError("BB required to check nested function def!")

        func_def = check_nested_func_def(node, self.bb, self.ctx)
        self.ctx.locals[func_def.name] = Variable(func_def.name, func_def.ty, func_def)
        return func_def

    def visit_ModifiedBlock(self, node: ModifiedBlock) -> ast.stmt:
        from guppylang_internals.checker.modifier_checker import check_modified_block

        if not self.bb:
            raise InternalGuppyError("BB required to check with block!")

        # check the body of the modified block
        modified_block = check_modified_block(node, self.bb, self.ctx)

        # check the arguments of the control and power.
        for control in modified_block.control:
            ctrl = control.ctrl
            # This case is handled during CFG construction.
            assert len(ctrl) > 0
            ctrl[0], ty = self._synth_expr(ctrl[0])

            if is_array_type(ty):
                if len(ctrl) > 1:
                    span = Span(to_span(control.func).end, to_span(control).end)
                    raise GuppyError(WrongNumberOfArgsError(span, 1, len(control.args)))
                element_ty = get_element_type(ty)
                if not is_qubit_ty(element_ty):
                    n = ExistentialConstVar.fresh(
                        "n", NumericType(NumericType.Kind.Nat)
                    )
                    dummy_array_ty = array_type(qubit_ty(), n)
                    raise GuppyTypeError(TypeMismatchError(ctrl[0], dummy_array_ty, ty))
                control.qubit_num = get_array_length(ty)
            else:
                for i in range(len(ctrl)):
                    ctrl[i], subst = self._check_expr(ctrl[i], qubit_ty())
                    assert len(subst) == 0
                control.qubit_num = len(ctrl)

        for power in node.power:
            power.iter, subst = self._check_expr(
                power.iter, NumericType(NumericType.Kind.Nat)
            )
            assert len(subst) == 0

        return modified_block

    def visit_If(self, node: ast.If) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_While(self, node: ast.While) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_Break(self, node: ast.Break) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_Continue(self, node: ast.Continue) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")


T = TypeVar("T")


def all_equal(xs: Iterable[T]) -> bool:
    """Checks if all elements yielded from an iterable are equal."""
    it = iter(xs)
    try:
        first = next(it)
    except StopIteration:
        return True
    return all(first == x for x in it)


def parse_unpack_pattern(lhs: ast.Tuple | ast.List) -> UnpackPattern:
    """Parses the LHS of an unpacking assignment like `a, *bs, c = ...` or
    `[a, *bs, c] = ...`."""
    # Split up LHS into `left, *starred, right` (the Python grammar ensures
    # that there is at most one starred expression)
    left = list(takewhile(lambda e: not isinstance(e, ast.Starred), lhs.elts))
    starred = (
        cast("ast.Starred", lhs.elts[len(left)]).value
        if len(left) < len(lhs.elts)
        else None
    )
    right = lhs.elts[len(left) + 1 :]
    assert isinstance(starred, ast.Name | None), "Python grammar"
    return UnpackPattern(left, starred, right)


def check_iter_unpack_has_static_size(expr: ast.expr, ctx: Context) -> int:
    """Helper function to check that an iterable expression is suitable to be unpacked
    in an assignment.

    This is the case if the iterator has a static, non-generic size.

    Returns the size of the iterator or emits a user error if the iterable is not
    suitable.
    """
    expr_synth = ExprSynthesizer(ctx)
    make_iter = with_loc(expr, MakeIter(expr, expr, unwrap_size_hint=False))
    make_iter, iter_ty = expr_synth.visit_MakeIter(make_iter)
    err = UnpackableError(expr, get_type(expr))
    if not is_sized_iter_type(iter_ty):
        err.add_sub_diagnostic(UnpackableError.NonStaticIter(None))
        raise GuppyError(err)
    match get_iter_size(iter_ty):
        case ConstValue(value=int(size)):
            return size
        case generic_size:
            err.add_sub_diagnostic(UnpackableError.GenericSize(None, generic_size))
            raise GuppyError(err)
