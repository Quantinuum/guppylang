"""Tests for array_swap functionality and error cases."""

from guppylang.decorator import guppy
from guppylang.std.array import array, array_swap


def test_basic_swap(validate, run_int_fn):
    """Verify basic swap compiles and produces the correct result."""

    @guppy
    def swap_first_last() -> array[int, 5]:
        arr = array(1, 2, 3, 4, 5)
        array_swap(arr, 0, 4)
        return arr

    @guppy
    def main() -> int:
        arr = swap_first_last()
        return arr[0]

    validate(swap_first_last.compile())
    run_int_fn(main, 5)


def test_multiple_swaps(run_int_fn):
    """Test multiple swaps in sequence produce the correct result."""

    @guppy
    def main() -> int:
        arr = array(1, 2, 3, 4, 5)
        array_swap(arr, 0, 4)  # [5, 2, 3, 4, 1]
        array_swap(arr, 1, 3)  # [5, 4, 3, 2, 1]
        return arr[1]

    run_int_fn(main, 4)


def test_uses_hugr_swap_op(validate):
    """Verify compilation uses HUGR's native swap operation."""

    @guppy
    def use_swap() -> None:
        arr = array(5, 10, 15, 20)
        array_swap(arr, 0, 3)

    hugr = use_swap.compile()
    validate(hugr)
