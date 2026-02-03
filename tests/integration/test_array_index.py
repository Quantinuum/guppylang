"""
Comprehensive unit tests for ArrayIndexChecker class.
"""

from guppylang import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, measure, h, discard_array


def test_valid_index_zero():
    @guppy
    def main() -> int:
        arr = array(42 for _ in range(5))
        return arr[0]

    main.compile()  # Should succeed


def test_valid_index_last():
    @guppy
    def main() -> int:
        arr = array(i * 2 for i in range(10))
        return arr[9]  # Last valid index for size 10

    main.compile()  # Should succeed


def test_valid_index_middle():
    @guppy
    def main() -> int:
        arr = array(i for i in range(100))
        return arr[50]

    main.compile()  # Should succeed


def test_valid_multiple_indexes():
    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        x = arr[0]
        y = arr[5]
        z = arr[9]
        return x + y + z

    main.compile()  # Should succeed


def test_setitem_valid_index():
    @guppy
    def main() -> None:
        arr = array(0 for _ in range(5))
        arr[0] = 42
        arr[4] = 99

    main.compile()  # Should succeed


def test_runtime_index_in_helper():
    @guppy
    def get_value(arr: array[int, 10], idx: int) -> int:
        return arr[idx]  # Runtime index

    @guppy
    def main() -> int:
        arr = array(i * 2 for i in range(10))
        return get_value(arr, 5)

    main.compile()  # Should succeed


def test_valid_computed_variable_index():
    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        x = 5
        return arr[x]  # x is assigned, not a literal - no static check

    main.compile()  # Should succeed


def test_invalid_computed_variable_index():
    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        x = 50
        return arr[x]  # x is assigned, not a literal - no static check

    main.compile()  # Should succeed


def test_nested_array_valid():
    @guppy
    def main() -> int:
        matrix = array(array(i + j for i in range(10)) for j in range(5))
        return matrix[1][2]  # Outer array has size 5

    main.compile()  # Should succeed


def test_index_zero_on_large_array():
    @guppy
    def main() -> int:
        arr = array(i for i in range(1000))
        return arr[0]

    main.compile()  # Should succeed


def test_method_is_borrowed_valid_index():
    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        result = qs.is_borrowed(3)  # Valid index
        discard_array(qs)

    main.compile()  # Should succeed


def test_method_take_valid_index():
    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        q = qs.take(5)  # inbounds, take qubit out of array
        measure(q)
        discard_array(qs)

    main.compile()


def test_method_put_valid_index():
    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        qs.put(qubit(), 0)  # Put a fresh qubit back into the array
        discard_array(qs)

    main.compile()  # Should succeed


def test_method_take_put_valid_index():
    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        measure(qs.take(3))  # Take it out to make space for the new one
        qs.put(qubit(), 3)
        h(qs[3])
        discard_array(qs)

    main.compile()  # Should succeed
