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


def test_kind_str():
    # NoneType -> str(self) = "None"
    assert NoneType().kind_str() == "None"

    # NumericType -> str(self) = "int" / "float" / "nat"
    assert NumericType(NumericType.Kind.Int).kind_str() == "int"
    assert NumericType(NumericType.Kind.Float).kind_str() == "float"
    assert NumericType(NumericType.Kind.Nat).kind_str() == "nat"

    # TupleType -> "Tuple"
    assert TupleType([NumericType(NumericType.Kind.Int)]).kind_str() == "Tuple"

    # FunctionType -> "Function"
    ty = FunctionType(
        inputs=[FuncInput(NumericType(NumericType.Kind.Int), InputFlags.NoFlags)],
        output=NumericType(NumericType.Kind.Int),
    )
    assert ty.kind_str() == "Function"

    # OpaqueType -> str(self), e.g. "array[int, 1]"
    ty_param = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    len_param = ConstParam(1, "n", NumericType(NumericType.Kind.Nat))
    array_ty = OpaqueType([ty_param.to_bound(0), len_param.to_bound(1)], array_type_def)
    assert array_ty.kind_str() == str(array_ty)

    # BoundTypeVar -> display_name
    bound_var = BoundTypeVar("T", 0, copyable=True, droppable=True)
    assert bound_var.kind_str() == "T"

    # ExistentialTypeVar -> "?T"
    ex_var = ExistentialTypeVar.fresh("T", copyable=True, droppable=True)
    assert ex_var.kind_str() == str(ex_var)
