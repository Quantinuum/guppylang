"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import hugr.std.collections.list
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections.list import List, ListVal

from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.arithmetic import (
    convert_ifromusize,
    convert_itousize,
)
from guppylang_internals.std._internal.compiler.prelude import (
    build_unwrap,
    build_unwrap_left,
    build_unwrap_right,
)
from guppylang_internals.tys.arg import TypeArg

if TYPE_CHECKING:
    from hugr.build.dfg import DfBase


# ------------------------------------------------------
# --------- std.collections operations -----------------
# ------------------------------------------------------


def _instantiate_list_op(
    name: str, elem_type: ht.Type, inp: list[ht.Type], out: list[ht.Type]
) -> ops.ExtOp:
    op_def = hugr.std.collections.list.EXTENSION.get_op(name)
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.TypeTypeArg(elem_type)],
    )


def list_pop(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `pop` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "pop", elem_type, [list_type], [list_type, ht.Option(elem_type)]
    )


def list_push(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `push` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op("push", elem_type, [list_type, elem_type], [list_type])


def list_get(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `get` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "get", elem_type, [list_type, ht.USize()], [ht.Option(elem_type)]
    )


def list_set(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `set` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "set",
        elem_type,
        [list_type, ht.USize(), elem_type],
        [list_type, ht.Either([elem_type], [elem_type])],
    )


def list_insert(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `insert` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "insert",
        elem_type,
        [list_type, ht.USize(), elem_type],
        [list_type, ht.Either([elem_type], [ht.Unit])],
    )


def list_length(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `length` operation."""
    list_type = List(elem_type)
    return _instantiate_list_op(
        "length", elem_type, [list_type], [list_type, ht.USize()]
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class ListGetitemCompiler(CustomCallCompiler):
    """Compiler for the `list.__getitem__` function."""

    def build_classical_getitem(
        self,
        list_wire: Wire,
        idx: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.__getitem__` for classical lists."""
        idx = self.builder.add_op(convert_itousize(), idx)
        result = self.builder.add_op(list_get(elem_ty), list_wire, idx)
        elem = build_unwrap(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[elem], inout_returns=[list_wire])

    def build_linear_getitem(
        self,
        list_wire: Wire,
        idx: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.__getitem__` for linear lists."""
        # Swap out the element at the given index with `None`. The `to_hugr`
        # implementation of the list type ensures that linear element types are turned
        # into optionals.
        elem_opt_ty = ht.Option(elem_ty)
        none = self.builder.add_op(ops.Tag(0, elem_opt_ty))
        idx = self.builder.add_op(convert_itousize(), idx)
        list_wire, result = self.builder.add_op(
            list_set(elem_opt_ty), list_wire, idx, none
        )
        elem_opt = build_unwrap_right(self.builder, result, "List index out of bounds")
        elem = build_unwrap(
            self.builder, elem_opt, "Linear list element has already been used"
        )
        return CallReturnWires(regular_returns=[elem], inout_returns=[list_wire])

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire, idx] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if elem_ty_arg.ty.linear:
            return self.build_linear_getitem(
                list_wire, idx, elem_ty_arg.ty.to_hugr(self.ctx)
            )
        else:
            return self.build_classical_getitem(
                list_wire, idx, elem_ty_arg.ty.to_hugr(self.ctx)
            )

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListSetitemCompiler(CustomCallCompiler):
    """Compiler for the `list.__setitem__` function."""

    def build_classical_setitem(
        self,
        list_wire: Wire,
        idx: Wire,
        elem: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.__setitem__` for classical lists."""
        idx = self.builder.add_op(convert_itousize(), idx)
        list_wire, result = self.builder.add_op(list_set(elem_ty), list_wire, idx, elem)
        # Unwrap the result, but we don't have to hold onto the returned old value
        build_unwrap_right(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[], inout_returns=[list_wire])

    def build_linear_setitem(
        self,
        list_wire: Wire,
        idx: Wire,
        elem: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `array.__setitem__` for linear arrays."""
        # Embed the element into an optional
        elem_opt_ty = ht.Option(elem_ty)
        elem = self.builder.add_op(ops.Some(elem_ty), elem)
        idx = self.builder.add_op(convert_itousize(), idx)
        list_wire, result = self.builder.add_op(
            list_set(elem_opt_ty), list_wire, idx, elem
        )
        old_elem_opt = build_unwrap_right(
            self.builder, result, "List index out of bounds"
        )
        # Check that the old element was `None`
        build_unwrap_left(
            self.builder, old_elem_opt, "Linear list element has not been used"
        )
        return CallReturnWires(regular_returns=[], inout_returns=[list_wire])

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire, idx, elem] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if elem_ty_arg.ty.linear:
            return self.build_linear_setitem(
                list_wire, idx, elem, elem_ty_arg.ty.to_hugr(self.ctx)
            )
        else:
            return self.build_classical_setitem(
                list_wire, idx, elem, elem_ty_arg.ty.to_hugr(self.ctx)
            )

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListPopCompiler(CustomCallCompiler):
    """Compiler for the `list.pop` function."""

    def build_classical_pop(
        self,
        list_wire: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.pop` for classical lists."""
        list_wire, result = self.builder.add_op(list_pop(elem_ty), list_wire)
        elem = build_unwrap(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[elem], inout_returns=[list_wire])

    def build_linear_pop(
        self,
        list_wire: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.pop` for linear lists."""
        elem_opt_ty = ht.Option(elem_ty)
        list_wire, result = self.builder.add_op(list_pop(elem_opt_ty), list_wire)
        elem_opt = build_unwrap(self.builder, result, "List index out of bounds")
        elem = build_unwrap(
            self.builder, elem_opt, "Linear list element has already been used"
        )
        return CallReturnWires(regular_returns=[elem], inout_returns=[list_wire])

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if elem_ty_arg.ty.linear:
            return self.build_linear_pop(list_wire, elem_ty_arg.ty.to_hugr(self.ctx))
        else:
            return self.build_classical_pop(list_wire, elem_ty_arg.ty.to_hugr(self.ctx))

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListPushCompiler(CustomCallCompiler):
    """Compiler for the `list.push` function."""

    def build_classical_push(
        self,
        list_wire: Wire,
        elem: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.push` for classical lists."""
        list_wire = self.builder.add_op(list_push(elem_ty), list_wire, elem)
        return CallReturnWires(regular_returns=[], inout_returns=[list_wire])

    def build_linear_push(
        self,
        list_wire: Wire,
        elem: Wire,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `list.push` for linear lists."""
        # Wrap element into an optional
        elem_opt_ty = ht.Option(elem_ty)
        elem_opt = self.builder.add_op(ops.Some(elem_ty), elem)
        list_wire = self.builder.add_op(list_push(elem_opt_ty), list_wire, elem_opt)
        return CallReturnWires(regular_returns=[], inout_returns=[list_wire])

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire, elem] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if elem_ty_arg.ty.linear:
            return self.build_linear_push(
                list_wire, elem, elem_ty_arg.ty.to_hugr(self.ctx)
            )
        else:
            return self.build_classical_push(
                list_wire, elem, elem_ty_arg.ty.to_hugr(self.ctx)
            )

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ListLengthCompiler(CustomCallCompiler):
    """Compiler for the `list.__len__` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [list_wire] = args
        [elem_ty_arg] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        elem_ty = elem_ty_arg.ty.to_hugr(self.ctx)
        if elem_ty_arg.ty.linear:
            elem_ty = ht.Option(elem_ty)
        list_wire, length = self.builder.add_op(list_length(elem_ty), list_wire)
        length = self.builder.add_op(convert_ifromusize(), length)
        return CallReturnWires(regular_returns=[length], inout_returns=[list_wire])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


def list_new(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type, args: list[Wire]
) -> Wire:
    if elem_type.type_bound() == ht.TypeBound.Linear:
        return _list_new_linear(builder, elem_type, args)
    else:
        return _list_new_classical(builder, elem_type, args)


def _list_new_classical(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type, args: list[Wire]
) -> Wire:
    # This may be simplified in the future with a `new` or `with_capacity` list op
    # See https://github.com/quantinuum/hugr/issues/1508
    lst = builder.load(ListVal([], elem_ty=elem_type))
    push_op = list_push(elem_type)
    for elem in args:
        lst = builder.add_op(push_op, lst, elem)
    return lst


def _list_new_linear(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type, args: list[Wire]
) -> Wire:
    elem_opt_ty = ht.Option(elem_type)
    lst = builder.load(ListVal([], elem_ty=elem_opt_ty))
    push_op = list_push(elem_opt_ty)
    for elem in args:
        elem_opt = builder.add_op(ops.Some(elem_type), elem)
        lst = builder.add_op(push_op, lst, elem_opt)
    return lst
