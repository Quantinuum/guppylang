from guppylang.decorator import guppy
from guppylang_internals.decorator import hugr_op
from guppylang_internals.std._internal.util import int_op
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NumericType,
)
from guppylang_internals.error import GuppyTypeError

# Define custom signature for iadd operation
ty = FunctionType(
    params=[],
    inputs=[
        FuncInput(NumericType(kind=NumericType.Kind.Int), InputFlags.NoFlags),
        FuncInput(NumericType(kind=NumericType.Kind.Int), InputFlags.NoFlags),
    ],
    output=NumericType(kind=NumericType.Kind.Int),
)


# Create hugr_op using custom signature
@hugr_op(int_op("iadd"), signature=ty)
def fake_iadd(*args) -> None: ...


def test_custom_signature_success(validate):
    @guppy
    def test_func() -> None:
        fake_iadd(1, 1)

    validate(test_func.compile_function())


def test_custom_signature_fail(validate):
    @guppy
    def test_func_fail() -> None:
        fake_iadd(1.0, 1.0)

    try:
        validate(test_func_fail.compile_function())
    except GuppyTypeError as e:
        assert True
