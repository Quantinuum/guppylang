"""Explicit cleanup for droppable values containing linear list handles."""

from typing import Any

from hugr import Hugr, Wire, ops
from hugr import tys as ht
from hugr.build import function as hf
from hugr.build.dfg import DfBase
from hugr.std.collections.array import EXTENSION as ARRAY_EXTENSION
from hugr.std.collections.borrow_array import EXTENSION as BORROW_ARRAY_EXTENSION
from hugr.std.int import IntVal

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.arithmetic import convert_itousize
from guppylang_internals.std._internal.compiler.array import (
    barray_borrow,
    barray_discard_all_borrowed,
    barray_is_borrowed,
)
from guppylang_internals.std._internal.compiler.list import (
    list_discard_empty,
    list_pop,
)
from guppylang_internals.std._internal.compiler.list_extension import EXTENSION
from guppylang_internals.std._internal.compiler.tket_exts import GUPPY_EXTENSION


def contains_list(ty: ht.Type) -> bool:
    """Whether a value contains a list that needs explicit draining."""
    match ty:
        case ht.ExtType(type_def=definition, args=args):
            return definition.qualified_name() == EXTENSION.get_type(
                "List"
            ).qualified_name() or any(
                contains_list(arg.ty) for arg in args if isinstance(arg, ht.TypeTypeArg)
            )
        case ht.Sum(variant_rows=rows):
            return any(contains_list(t) for row in rows for t in row)
        case _:
            return False


def define_drop(hugr: Hugr[Any], ty: ht.Type, index: int) -> hf.Function:
    """Build a private cleanup function for a checker-approved droppable value."""
    function = hf.Module(hugr).define_function(f"__guppy_list_drop_{index}", [ty], [])
    _drop(function, function.inputs()[0], ty)
    function.set_outputs()
    return function


def _drop(builder: DfBase[Any], wire: Wire, ty: ht.Type) -> None:
    if ty.type_bound() == ht.TypeBound.Copyable:
        return
    match ty:
        case ht.ExtType(type_def=definition, args=[ht.TypeTypeArg(elem_ty)]) if (
            definition.qualified_name() == EXTENSION.get_type("List").qualified_name()
        ):
            # Pop until None. Each Some payload is disposed of recursively before
            # continuing, so discard_empty only receives an exhausted handle.
            loop = builder.add_tail_loop([], [wire])
            lst, elem = loop.add_op(list_pop(elem_ty)[0], loop.inputs()[0])
            cond = loop.add_conditional(elem, lst)
            empty = cond.add_case(0)
            empty.set_outputs(empty.add_op(ops.Tag(1, ht.UnitSum(2))), *empty.inputs())
            some = cond.add_case(1)
            value, lst = some.inputs()
            _drop(some, value, elem_ty)
            some.set_outputs(some.add_op(ops.Tag(0, ht.UnitSum(2))), lst)
            loop.set_loop_outputs(*cond.outputs())
            builder.add_op(list_discard_empty(elem_ty)[0], loop)
        case ht.Sum(variant_rows=rows):
            cond = builder.add_conditional(wire)
            for index, row in enumerate(rows):
                case = cond.add_case(index)
                for value, elem_ty in zip(case.inputs(), row, strict=True):
                    _drop(case, value, elem_ty)
                case.set_outputs()
        case ht.ExtType(
            type_def=definition,
            args=[ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)],
        ) if (
            definition.qualified_name()
            == BORROW_ARRAY_EXTENSION.get_type("borrow_array").qualified_name()
        ):
            # Moved-out array slots are already borrowed. Skip those slots and
            # dispose of the remaining elements before freeing the backing array.
            size = ht.BoundedNatArg(length)
            for index in range(length):
                idx = builder.add_op(
                    convert_itousize()[0], builder.load(IntVal(index, width=6))
                )
                wire, borrowed = builder.add_op(
                    barray_is_borrowed(elem_ty, size)[0], wire, idx
                )
                cond = builder.add_conditional(borrowed, wire)
                present = cond.add_case(0)
                arr, elem = present.add_op(
                    barray_borrow(elem_ty, size)[0], present.inputs()[0], idx
                )
                _drop(present, elem, elem_ty)
                present.set_outputs(arr)
                absent = cond.add_case(1)
                absent.set_outputs(*absent.inputs())
                wire = cond
            builder.add_op(barray_discard_all_borrowed(elem_ty, size)[0], wire)
        case ht.ExtType(
            type_def=definition,
            args=[ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)],
        ) if (
            definition.qualified_name()
            == ARRAY_EXTENSION.get_type("array").qualified_name()
        ):
            unpack = ARRAY_EXTENSION.get_op("unpack").instantiate(
                [ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)],
                ht.FunctionType([ty], [elem_ty] * length),
            )
            for elem in builder.add_op(unpack, wire):
                _drop(builder, elem, elem_ty)
        case _:
            if contains_list(ty):
                raise InternalGuppyError(f"Cannot dispose of list-containing type {ty}")
            builder.add_op(
                GUPPY_EXTENSION.get_op("drop").instantiate(
                    [ht.TypeTypeArg(ty)], ht.FunctionType([ty], [])
                ),
                wire,
            )
