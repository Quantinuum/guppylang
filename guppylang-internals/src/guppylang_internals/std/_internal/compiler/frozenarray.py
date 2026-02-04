"""Compilers building frozenarray functions on top of hugr standard operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections.static_array import EXTENSION, StaticArray

from guppylang_internals.compiler.core import (
    GlobalConstId,
)
from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang_internals.std._internal.compiler.arithmetic import (
    INT_T,
    convert_itousize,
)
from guppylang_internals.std._internal.compiler.prelude import (
    build_unwrap,
)
from guppylang_internals.tys.arg import TypeArg

if TYPE_CHECKING:
    from hugr.build import function as hf


def static_array_get(elem_ty: ht.Type) -> ops.ExtOp:
    """Returns the static array `get` operation."""
    assert elem_ty.type_bound() == ht.TypeBound.Copyable
    arr_ty = StaticArray(elem_ty)
    return EXTENSION.get_op("get").instantiate(
        [ht.TypeTypeArg(elem_ty)],
        ht.FunctionType([arr_ty, ht.USize()], [ht.Option(elem_ty)]),
    )


FROZENARRAY_GETITEM: Final[GlobalConstId] = GlobalConstId.fresh(
    "frozenarray.__getitem__"
)


class FrozenarrayGetitemCompiler(CustomCallCompiler):
    def getitem_func(self) -> hf.Function:
        var = ht.Variable(0, ht.TypeBound.Copyable)
        sig = ht.PolyFuncType(
            params=[ht.TypeTypeParam(ht.TypeBound.Copyable)],
            body=ht.FunctionType([StaticArray(var), INT_T], [var]),
        )
        func, already_exists = self.ctx.declare_global_func(FROZENARRAY_GETITEM, sig)
        if not already_exists:
            [arr, idx] = func.inputs()
            idx = func.add_op(convert_itousize(), idx)
            elem_opt = func.add_op(static_array_get(var), arr, idx)
            elem = build_unwrap(func, elem_opt, "Frozenarray index out of bounds")
            func.set_outputs(elem)
        return func

    def compile(self, args: list[Wire]) -> list[Wire]:
        [ty_arg, _] = self.type_args
        assert isinstance(ty_arg, TypeArg)
        elem_ty = ty_arg.ty.to_hugr(self.ctx)
        inst = ht.FunctionType([StaticArray(elem_ty), INT_T], [elem_ty])
        type_args = [ht.TypeTypeArg(elem_ty)]
        elem = self.builder.call(
            self.getitem_func(), *args, instantiation=inst, type_args=type_args
        )
        return [elem]
