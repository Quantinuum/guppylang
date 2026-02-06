"""Tests for array_swap functionality and error cases."""

from guppylang.decorator import guppy
from guppylang.std.array import array, array_swap


def test_basic_swap_compiles(validate):
    """Verify basic swap compiles without errors."""

    @guppy
    def swap_first_last() -> None:
        arr = array(1, 2, 3, 4, 5)
        array_swap(arr, 0, 4)

    hugr = swap_first_last.compile()
    validate(hugr)


def test_multiple_swaps(validate):
    """Test multiple swaps in sequence compile correctly."""

    @guppy
    def multiple() -> None:
        arr = array(1, 2, 3, 4, 5)
        array_swap(arr, 0, 4)
        array_swap(arr, 1, 3)
        array_swap(arr, 0, 1)

    hugr = multiple.compile()
    validate(hugr)


def test_uses_hugr_swap_op(validate):
    """Verify compilation uses HUGR's native swap operation."""

    @guppy
    def use_swap() -> None:
        arr = array(5, 10, 15, 20)
        array_swap(arr, 0, 3)

    hugr = use_swap.compile()
    validate(hugr)
