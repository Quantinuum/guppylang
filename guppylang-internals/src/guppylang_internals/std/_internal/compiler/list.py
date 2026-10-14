"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hugr import Wire
from hugr import tys as ht
from hugr.ops import ExtOp

from guppylang_internals.compiler.builder import OpWithEffects, ops, pure
from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.arithmetic import (
    convert_ifromusize,
    convert_itousize,
)
from guppylang_internals.std._internal.compiler.list_extension import EXTENSION, List
from guppylang_internals.std._internal.compiler.prelude import (
    build_unwrap,
    build_unwrap_right,
)
from guppylang_internals.tys.arg import TypeArg

if TYPE_CHECKING:
    from guppylang_internals.compiler.builder import DFBuilder


# ------------------------------------------------------
# --------- std.collections operations -----------------
# ------------------------------------------------------


def _instantiate_list_op(
    name: str, elem_type: ht.Type, inp: list[ht.Type], out: list[ht.Type]
) -> OpWithEffects:
    op_def = EXTENSION.get_op(name)
    return pure(
        ExtOp(
            op_def,
            ht.FunctionType(inp, out),
            [ht.TypeTypeArg(elem_type)],
        )
    )


def list_pop(elem_type: ht.Type) -> OpWithEffects:
    """Returns a list `pop` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "pop", elem_type, [list_type], [list_type, ht.Option(elem_type)]
    )


def list_push(elem_type: ht.Type) -> OpWithEffects:
    """Returns a list `push` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op("push", elem_type, [list_type, elem_type], [list_type])


def list_get(elem_type: ht.Type) -> OpWithEffects:
    """Returns a list `get` operation."""
    if elem_type.type_bound() != ht.TypeBound.Copyable:
        raise InternalGuppyError("List get requires copyable elements")
    list_type = List(elem_type)
    return _instantiate_list_op(
        "get", elem_type, [list_type, ht.USize()], [list_type, ht.Option(elem_type)]
    )


def list_set(elem_type: ht.Type) -> OpWithEffects:
    """Returns a list `set` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "set",
        elem_type,
        [list_type, ht.USize(), elem_type],
        # Return supplied element if out of range else element removed from list
        [list_type, ht.Either([elem_type], [elem_type])],
    )


def list_insert(elem_type: ht.Type) -> OpWithEffects:
    """Returns a list `insert` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "insert",
        elem_type,
        [list_type, ht.USize(), elem_type],
        # Return supplied element if out of range else unit
        [list_type, ht.Either([elem_type], [])],
    )


def list_length(elem_type: ht.Type) -> OpWithEffects:
    """Returns a list `length` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "length", elem_type, [list_type], [list_type, ht.USize()]
    )


def list_new_op(elem_type: ht.Type) -> OpWithEffects:
    """Constructs an empty list of arbitrary elements at runtime."""
    return _instantiate_list_op("new", elem_type, [], [List(elem_type)])


def list_discard_empty(elem_type: ht.Type) -> OpWithEffects:
    """Consumes an empty list, panicking if it still contains elements."""
    op, _ = _instantiate_list_op("discard_empty", elem_type, [List(elem_type)], [])
    from guppylang_internals.tys import Effect

    return op, [Effect.ANY]


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class ListGetitemCompiler(CustomCallCompiler):
    """Copy a copyable element by index while returning the list handle."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        list_wire, idx = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if not elem_ty_arg.ty.copyable:
            raise InternalGuppyError("List indexed reads require copyable elements")
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        idx = self.builder.add_op(convert_itousize(), idx)
        list_wire, result = self.builder.add_op(list_get(elem_ty), list_wire, idx)
        elem = build_unwrap(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[elem], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListSetitemCompiler(CustomCallCompiler):
    """Replace a droppable element, disposing of the returned prior value."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        list_wire, idx, elem = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if not elem_ty_arg.ty.droppable:
            raise InternalGuppyError("List assignment requires droppable elements")
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        idx = self.builder.add_op(convert_itousize(), idx)
        list_wire, result = self.builder.add_op(list_set(elem_ty), list_wire, idx, elem)
        # The genuine swap result is unwrapped. Drop insertion disposes of a
        # droppable prior value, recursively draining any list handles it owns.
        build_unwrap_right(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListSwapCompiler(CustomCallCompiler):
    """Replace an element and transfer the prior element to the caller."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        list_wire, idx, elem = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        idx = self.builder.add_op(convert_itousize(), idx)
        list_wire, result = self.builder.add_op(list_set(elem_ty), list_wire, idx, elem)
        old = build_unwrap_right(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[old], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListPopCompiler(CustomCallCompiler):
    """Remove and transfer the last element, panicking when the list is empty."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        list_wire, result = self.builder.add_op(list_pop(elem_ty), list_wire)
        elem = build_unwrap(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[elem], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListPushCompiler(CustomCallCompiler):
    """Transfer an element directly into the list."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        list_wire, elem = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        list_wire = self.builder.add_op(
            list_push(elem_ty_arg.ty.to_hugr(self.ctx)), list_wire, elem
        )
        return CallReturnWires(regular_returns=[], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListLengthCompiler(CustomCallCompiler):
    """Compiler for the `list.__len__` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        list_wire, length = self.builder.add_op(list_length(elem_ty), list_wire)
        length = self.builder.add_op(convert_ifromusize(), length)
        return CallReturnWires(regular_returns=[length], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListDiscardEmptyCompiler(CustomCallCompiler):
    """Compiler for consuming an empty list without discarding any elements."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        self.builder.add_op(list_discard_empty(elem_ty), *args)
        return []


class ListIterCompiler(CustomCallCompiler):
    """Prepare a consuming iterator that yields elements in insertion order."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        [lst] = args
        ty = self.builder.get_wire_type(lst)
        assert isinstance(ty, List)
        elem_ty = ty.ty
        reversed_list = self.builder.add_op(list_new_op(elem_ty))
        loop = self.builder.add_tail_loop([lst], [reversed_list])
        lst, reversed_list = loop.inputs()
        lst, elem = loop.add_op(list_pop(elem_ty), lst)
        cond = loop.add_conditional(elem, lst, reversed_list)
        empty = cond.add_case(0)
        lst, reversed_list = empty.inputs()
        empty.add_op(list_discard_empty(elem_ty), lst)
        predicate = empty.add_op(ops.tag(1, ht.Either([List(elem_ty)], [])))
        empty.set_outputs(predicate, reversed_list)
        some = cond.add_case(1)
        elem, lst, reversed_list = some.inputs()
        reversed_list = some.add_op(list_push(elem_ty), reversed_list, elem)
        predicate = some.add_op(ops.tag(0, ht.Either([List(elem_ty)], [])), lst)
        some.set_outputs(predicate, reversed_list)
        predicate, reversed_list = cond.outputs()
        loop.set_loop_outputs(predicate, reversed_list)
        return list(loop.outputs())


class ListNextCompiler(CustomCallCompiler):
    """Pop the next iterator element and release the handle on exhaustion."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        [lst] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        list_ty = List(elem_ty)
        result_ty = ht.Option(ht.Tuple(elem_ty, list_ty))
        lst, elem = self.builder.add_op(list_pop(elem_ty), lst)
        cond = self.builder.add_conditional(elem, lst)
        empty = cond.add_case(0)
        empty.add_op(list_discard_empty(elem_ty), empty.inputs()[0])
        empty.set_outputs(empty.add_op(ops.tag(0, result_ty)))
        some = cond.add_case(1)
        elem, lst = some.inputs()
        pair = some.add_op(ops.make_tuple([elem_ty, list_ty]), elem, lst)
        some.set_outputs(some.add_op(ops.tag(1, result_ty), pair))
        return list(cond.outputs())


def list_new(builder: DFBuilder, elem_type: ht.Type, args: list[Wire]) -> Wire:
    """Construct a list by transferring each supplied element directly into it."""
    lst = builder.add_op(list_new_op(elem_type))
    push_op = list_push(elem_type)
    for elem in args:
        lst = builder.add_op(push_op, lst, elem)
    return lst
