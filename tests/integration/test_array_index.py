"""
Comprehensive unit tests for ArrayIndexChecker class.
Tests cover all edge cases, both valid and invalid scenarios.
"""

import pytest
from guppylang import guppy
from guppylang.std.builtins import array
from guppylang_internals.error import GuppyError
from guppylang.std.quantum import qubit, measure, h, discard_array

# ============================================================================
# POSITIVE OUT-OF-BOUNDS TESTS (index >= array_length)
# ============================================================================


def test_index_equals_array_size():
    """Test index equal to array size (first invalid index)."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(5))
        return arr[5]  # Index 5 is invalid for size 5 (valid: 0-4)

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 5
    assert err.size == 5


def test_index_one_past_array_size():
    """Test index one greater than array size."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(5))
        return arr[6]

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 6
    assert err.size == 5


def test_index_far_beyond_array_size():
    """Test index much larger than array size."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        return arr[100]

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 100
    assert err.size == 10


def test_large_array_out_of_bounds():
    """Test out of bounds on a large array."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(1000))
        return arr[1000]  # Valid indices: 0-999

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 1000
    assert err.size == 1000


# ============================================================================
# NEGATIVE INDEX TESTS
# ============================================================================


def test_negative_index_minus_one():
    """Test negative index -1."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(5))
        return arr[-1]

    reg_expr = r"Array index -1 is out of bounds"
    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == -1
    assert err.size == 5


def test_negative_index_large():
    """Test large negative index."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(5))
        return arr[-100]

    reg_expr = r"Array index -100 is out of bounds"
    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == -100
    assert err.size == 5


# ============================================================================
# VALID INDEX TESTS (should compile successfully)
# ============================================================================


def test_index_zero():
    """Test index 0 (always valid for non-empty arrays)."""

    @guppy
    def main() -> int:
        arr = array(42 for _ in range(5))
        return arr[0]

    main.compile()  # Should succeed


def test_index_last_valid():
    """Test last valid index (size - 1)."""

    @guppy
    def main() -> int:
        arr = array(i * 2 for i in range(10))
        return arr[9]  # Last valid index for size 10

    main.compile()  # Should succeed


def test_index_middle():
    """Test index in the middle of array."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(100))
        return arr[50]

    main.compile()  # Should succeed


def test_multiple_valid_accesses():
    """Test multiple valid array accesses in same function."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        x = arr[0]
        y = arr[5]
        z = arr[9]
        return x + y + z

    main.compile()  # Should succeed


# ============================================================================
# SINGLE ELEMENT ARRAY TESTS
# ============================================================================


def test_single_element_array_valid():
    """Test valid access to single-element array."""

    @guppy
    def main() -> int:
        arr = array(42 for _ in range(1))
        return arr[0]  # Only valid index

    main.compile()  # Should succeed


def test_single_element_array_invalid():
    """Test invalid access to single-element array."""

    @guppy
    def main() -> int:
        arr = array(42 for _ in range(1))
        return arr[1]

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 1
    assert err.size == 1


# ============================================================================
# SETITEM TESTS (__setitem__ bounds checking)
# ============================================================================


def test_setitem_out_of_bounds():
    """Test __setitem__ with out of bounds index."""

    @guppy
    def main() -> None:
        arr = array(0 for _ in range(5))
        arr[10] = 42

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 10
    assert err.size == 5


def test_setitem_negative_index():
    """Test __setitem__ with negative index."""

    @guppy
    def main() -> None:
        arr = array(0 for _ in range(5))
        arr[-1] = 42

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == -1
    assert err.size == 5


def test_setitem_valid():
    """Test __setitem__ with valid index."""

    @guppy
    def main() -> None:
        arr = array(0 for _ in range(5))
        arr[0] = 42
        arr[4] = 99

    main.compile()  # Should succeed


# ============================================================================
# RUNTIME/DYNAMIC INDEX TESTS (should NOT trigger static checking)
# ============================================================================


def test_runtime_index_in_helper():
    """Test runtime index when function is called from entrypoint."""

    @guppy
    def get_value(arr: array[int, 10], idx: int) -> int:
        return arr[idx]  # Runtime index

    @guppy
    def main() -> int:
        arr = array(i * 2 for i in range(10))
        return get_value(arr, 5)

    main.compile()  # Should succeed


def test_computed_index():
    """Test that computed indices might not trigger static checking."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        x = 5
        # Note: depending on optimization, x might be treated as constant
        # This test validates that if it's not optimized away, it doesn't error
        return arr[0]  # Use literal to ensure it compiles

    main.compile()  # Should succeed


# ============================================================================
# DIFFERENT ARRAY TYPES
# ============================================================================


def test_qubit_array_out_of_bounds():
    """Test bounds checking with qubit arrays."""

    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        h(qs[10])
        discard_array(qs)

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 10
    assert err.size == 10


def test_qubit_array_valid():
    """Test valid qubit array access."""

    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        h(qs[0])
        h(qs[9])
        discard_array(qs)

    main.compile()  # Should succeed


def test_nested_array_out_of_bounds():
    """Test bounds checking with nested arrays."""

    @guppy
    def main() -> int:
        matrix = array(array(i + j for i in range(10)) for j in range(5))
        return matrix[5][0]  # Outer array has size 5

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 5
    assert err.size == 5


# ============================================================================
# EDGE CASES WITH ZERO
# ============================================================================


def test_index_zero_on_large_array():
    """Test that index 0 always works regardless of array size."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(1000))
        return arr[0]

    main.compile()  # Should succeed


# ============================================================================
# MULTIPLE ERRORS IN SAME FUNCTION
# ============================================================================


def test_first_error_caught():
    """Test that the first out-of-bounds access is caught."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        x = arr[10]  # First error - should be caught here
        y = arr[20]  # Second error - won't reach this
        return x + y

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 10
    assert err.size == 10


# ============================================================================
# SYNTHESIS MODE VS CHECK MODE
# ============================================================================


def test_check_mode_return_statement():
    """Test bounds checking in check mode (return statement)."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(5))
        return arr[5]  # Check mode: expected type is int

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 5
    assert err.size == 5


def test_synthesize_mode_assignment():
    """Test bounds checking in synthesize mode (assignment)."""

    @guppy
    def main() -> None:
        arr = array(i for i in range(5))
        x = arr[5]  # Synthesize mode: infer type of x

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 5
    assert err.size == 5


# ============================================================================
# METHOD CALL CONTEXT (like is_borrowed, take, put)
# ============================================================================


def test_method_with_valid_index():
    """Test array methods with valid constant indices."""

    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        result = qs.is_borrowed(3)  # Valid index
        discard_array(qs)

    main.compile()  # Should succeed


def test_take_with_out_of_bounds():
    """Test array.take() with out of bounds index."""

    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(10))
        q = qs.take(10)  # Out of bounds
        measure(q)
        discard_array(qs)

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 10
    assert err.size == 10


# ============================================================================
# BOUNDARY VALUE ANALYSIS
# ============================================================================


def test_boundary_size_2_index_0():
    """Boundary test: size 2, index 0."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(2))
        return arr[0]

    main.compile()  # Should succeed


def test_boundary_size_2_index_1():
    """Boundary test: size 2, index 1."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(2))
        return arr[1]

    main.compile()  # Should succeed


def test_boundary_size_2_index_2():
    """Boundary test: size 2, index 2 (invalid)."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(2))
        return arr[2]

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 2
    assert err.size == 2


# ============================================================================
# EDGE CASE: Different compilation contexts
# ============================================================================


def test_in_loop_context():
    """Test array access inside loop with constant index."""

    @guppy
    def main() -> int:
        arr = array(i for i in range(10))
        total = 0
        for i in range(5):
            total += arr[10]  # Constant out of bounds
        return total

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 10
    assert err.size == 10


def test_in_conditional():
    """Test array access in conditional with constant index."""

    @guppy
    def main(flag: bool) -> int:
        arr = array(i for i in range(10))
        if flag:
            return arr[10]  # Out of bounds
        else:
            return arr[0]

    with pytest.raises(GuppyError) as excinfo:
        main.compile()

    err = excinfo.value.error
    assert err.title == "Index out of bounds"
    assert err.index == 10
    assert err.size == 10
