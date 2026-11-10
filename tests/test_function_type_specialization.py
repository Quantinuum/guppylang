from guppylang_internals.tys.param import TypeParam
from guppylang_internals.tys.ty import (
    ExistentialTypeVar,
    FuncInput,
    FunctionType,
    InputFlags,
    NumericType,
)


def test_nested_function_input_substitution():
    var = ExistentialTypeVar.fresh("T", copyable=False, droppable=False)
    int_ty = NumericType(NumericType.Kind.Int)
    callback = FunctionType([FuncInput(var, InputFlags.Inout, "value")], int_ty)
    outer = FunctionType([FuncInput(callback, InputFlags.NoFlags)], int_ty)

    specialized = outer.substitute({var: int_ty})
    assert isinstance(specialized, FunctionType)
    nested = specialized.inputs[0].ty
    assert isinstance(nested, FunctionType)
    assert nested.inputs[0].ty == int_ty
    assert nested.inputs[0].flags == InputFlags.NoFlags
    assert nested.inputs[0].name == "value"


def test_partial_instantiation_preserves_unresolved_borrowing_and_ownership():
    t = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    u = TypeParam(1, "U", must_be_copyable=False, must_be_droppable=False)
    int_ty = NumericType(NumericType.Kind.Int)
    ty = FunctionType(
        [
            FuncInput(t.to_bound().ty, InputFlags.Inout, "borrowed"),
            FuncInput(u.to_bound().ty, InputFlags.Inout, "unresolved"),
            FuncInput(t.to_bound().ty, InputFlags.Owned, "owned"),
        ],
        int_ty,
        params=[t, u],
    )

    partial = ty.instantiate_partial([int_ty.to_arg(), None])
    assert [inp.flags for inp in partial.inputs] == [
        InputFlags.NoFlags,
        InputFlags.Inout,
        InputFlags.Owned,
    ]
    assert [inp.name for inp in partial.inputs] == ["borrowed", "unresolved", "owned"]
    assert len(partial.params) == 1
    assert partial.inputs[1].ty == partial.params[0].to_bound().ty


def test_existing_copyable_inout_is_preserved():
    int_ty = NumericType(NumericType.Kind.Int)
    ty = FunctionType([FuncInput(int_ty, InputFlags.Inout)], int_ty)

    transformed = ty.instantiate(())
    assert transformed.inputs[0].flags == InputFlags.Inout
    assert ty.substitute({}) == ty
