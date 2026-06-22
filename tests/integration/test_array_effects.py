"""Tests of effects annotation."""

import pytest

from guppylang_internals.error import GuppyTypeError

from guppylang.std.builtins import array
from guppylang.emulator.exceptions import EmulatorError
from guppylang.decorator import guppy, Effect


def test_pure_array_new(validate):
    @guppy(effects=[])
    def pure_func(x: int) -> array[int, 3]:
        return array(x, x, x)

    validate(pure_func.compile_function())


@pytest.mark.parametrize(
    ("fx", "err_type", "msg"),
    [
        ([], GuppyTypeError, "TooManyEffectsError"),
        ([Effect.ANY], EmulatorError, "Array element is already borrowed"),
    ],
)
def test_array_read_after_borrow(fx, err_type, msg, run_int_fn):
    @guppy.struct
    class MyStruct:
        i: int

    T = guppy.type_var("T", copyable=False)

    @guppy(effects=fx)
    def read(arr: array[T, 3]) -> T:
        return arr.take(1)

    @guppy
    def main() -> int:
        arr = array(MyStruct(1), MyStruct(2), MyStruct(3))
        read(arr)
        return arr[1].i

    with pytest.raises(err_type, match=msg):
        run_int_fn(main, expected=0xDEADBEEF)
