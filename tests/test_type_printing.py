from guppylang_internals.tys.builtin import array_type_def
from guppylang_internals.tys.param import ConstParam, TypeParam
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    ExistentialTypeVar,
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    TupleType,
)


def test_generic_function_type() -> None:
    ty_param = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    len_param = ConstParam(1, "n", NumericType(NumericType.Kind.Nat))
    array_ty = OpaqueType([ty_param.to_bound(0), len_param.to_bound(1)], array_type_def)
    ty = FunctionType(
        params=[ty_param, len_param],
        inputs=[FuncInput(array_ty, InputFlags.Inout)],
        output=ty_param.to_bound(0).ty,
    )
    assert str(ty) == "forall T, n: nat. array[T, n] -> T"


def test_comptime_function_type() -> None:
    ty_param = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    ty = FunctionType(
        inputs=[FuncInput(NumericType(NumericType.Kind.Nat), InputFlags.Comptime)],
        output=ty_param.to_bound(0).ty,
        params=[ty_param],
    )
    assert str(ty) == "forall T. nat @comptime -> T"


def test_kind_str() -> None:
    none_ty = NoneType()
    assert none_ty.kind_str() == "None"
    assert none_ty.kind_str() == str(none_ty)

    int_ty = NumericType(NumericType.Kind.Int)
    assert int_ty.kind_str() == "int"
    assert int_ty.kind_str() == str(int_ty)

    float_ty = NumericType(NumericType.Kind.Float)
    assert float_ty.kind_str() == "float"
    assert float_ty.kind_str() == str(float_ty)

    nat_ty = NumericType(NumericType.Kind.Nat)
    assert nat_ty.kind_str() == "nat"
    assert nat_ty.kind_str() == str(nat_ty)

    assert TupleType([NumericType(NumericType.Kind.Int)]).kind_str() == "Tuple"

    func_ty = FunctionType(
        inputs=[FuncInput(NumericType(NumericType.Kind.Int), InputFlags.NoFlags)],
        output=NumericType(NumericType.Kind.Int),
    )
    assert func_ty.kind_str() == "Function"

    ty_param = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    len_param = ConstParam(1, "n", NumericType(NumericType.Kind.Nat))
    array_ty = OpaqueType([ty_param.to_bound(0), len_param.to_bound(1)], array_type_def)
    assert array_ty.kind_str() == str(array_ty)

    bound_var = BoundTypeVar("T", 0, copyable=True, droppable=True)
    assert bound_var.kind_str() == "T"
    assert bound_var.kind_str() == str(bound_var)

    ex_var = ExistentialTypeVar.fresh("T", copyable=True, droppable=True)
    assert ex_var.kind_str() == str(ex_var)
