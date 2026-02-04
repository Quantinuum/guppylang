from guppylang_internals.tys.builtin import array_type_def
from guppylang_internals.tys.param import ConstParam, TypeParam
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NumericType,
    OpaqueType,
)


def test_generic_function_type():
    ty_param = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    len_param = ConstParam(1, "n", NumericType(NumericType.Kind.Nat))
    array_ty = OpaqueType([ty_param.to_bound(0), len_param.to_bound(1)], array_type_def)
    ty = FunctionType(
        params=[ty_param, len_param],
        inputs=[FuncInput(array_ty, InputFlags.Inout)],
        output=ty_param.to_bound(0).ty,
    )
    assert str(ty) == "forall T, n: nat. array[T, n] -> T"


def test_comptime_function_type():
    ty_param = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    ty = FunctionType(
        inputs=[FuncInput(NumericType(NumericType.Kind.Nat), InputFlags.Comptime)],
        output=ty_param.to_bound(0).ty,
        params=[ty_param],
    )
    assert str(ty) == "forall T. nat @comptime -> T"
