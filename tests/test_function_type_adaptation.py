import pytest
from guppylang_internals.tys.param import TypeParam
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    can_adapt_function,
)


@pytest.mark.parametrize("copyable", [False, True])
@pytest.mark.parametrize("droppable", [False, True])
def test_borrow_adaptation_capabilities(copyable: bool, droppable: bool) -> None:
    ty = TypeParam(0, "T", copyable, droppable).to_bound().ty
    borrowed = FunctionType([FuncInput(ty, InputFlags.Inout)], NoneType())
    consumed = FunctionType([FuncInput(ty, InputFlags.NoFlags)], NoneType())

    # A consuming callback must copy its borrowed input for write-back. A borrowed
    # callback used by value must discard the additional value it returns.
    assert can_adapt_function(consumed, borrowed) == copyable
    assert can_adapt_function(borrowed, consumed) == droppable
