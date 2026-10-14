import pytest

from guppylang import guppy, qubit
from guppylang.emulator import EmulatorError
from guppylang.std.array import array
from guppylang.std.quantum import discard, measure, x as quantum_x
from guppylang_internals.decorator import custom_function
from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.arithmetic import convert_itousize
from guppylang_internals.std._internal.compiler.list import list_insert, list_set
from guppylang.std.lang import owned
from guppylang_internals.std._internal.compiler.prelude import (
    build_unwrap_left,
    build_unwrap_right,
)
from guppylang_internals.tys import Effect


class InsertCompiler(CustomCallCompiler):
    """Exercise the extension's insert operation without adding a public Guppy API."""

    def compile_with_inouts(self, args):
        lst, idx, elem = args
        elem_ty = self.builder.get_wire_type(elem)
        assert elem_ty is not None
        idx = self.builder.add_op(convert_itousize(), idx)
        lst, result = self.builder.add_op(list_insert(elem_ty), lst, idx, elem)
        build_unwrap_right(self.builder, result, "List index out of bounds")
        return CallReturnWires(regular_returns=[], inout_returns=[lst])

    def compile(self, args):
        raise InternalGuppyError("Call compile_with_inouts instead")


@custom_function(InsertCompiler(), effects=[Effect.ANY])
def insert(xs: list[int], index: int, elem: int) -> None: ...


class FailedSetCompiler(CustomCallCompiler):
    """Test that failed HUGR set returns the supplied element and preserves the list."""

    def compile_with_inouts(self, args):
        lst, idx, elem = args
        elem_ty = self.builder.get_wire_type(elem)
        assert elem_ty is not None
        idx = self.builder.add_op(convert_itousize(), idx)
        lst, result = self.builder.add_op(list_set(elem_ty), lst, idx, elem)
        supplied = build_unwrap_left(self.builder, result, "Expected failed set")
        return CallReturnWires(regular_returns=[supplied], inout_returns=[lst])

    def compile(self, args):
        raise InternalGuppyError("Call compile_with_inouts instead")


@custom_function(FailedSetCompiler(), effects=[Effect.ANY])
def failed_set_for_test(xs: list[qubit], index: int, elem: qubit @ owned) -> qubit: ...


@custom_function(InsertCompiler(), effects=[Effect.ANY])
def insert_qubit_for_test(xs: list[qubit], index: int, elem: qubit @ owned) -> None: ...


@pytest.fixture(autouse=True)
def enable_lists(use_experimental_features):
    pass


def test_iteration_order(run_int_fn):
    @guppy
    def main() -> int:
        xs = [1, 2, 3]
        result = 0
        for x in xs:
            result = result * 10 + x
        return result

    run_int_fn(main, 123)


def test_mutation_and_handle_threading(run_int_fn):
    @guppy
    def main() -> int:
        xs = [1, 2]
        value = xs[0] + xs[1]
        xs.append(value)
        xs.__setitem__(0, 4)
        result = xs.pop() + xs[0] + len(xs)
        return result

    run_int_fn(main, 9)


def test_comprehension_and_cleanup(run_int_fn):
    @guppy
    def main() -> int:
        xs = [2 * i for i in range(5)]
        result = 0
        for x in xs:
            result += x
        return result

    run_int_fn(main, 20)


def test_early_iterator_cleanup(run_int_fn):
    @guppy
    def main() -> int:
        xs = [1, 2, 3]
        result = 0
        for x in xs:
            result = x
            break
        return result

    run_int_fn(main, 1)


def test_nested_replacement_and_cleanup(run_int_fn):
    @guppy
    def main() -> int:
        xs = [[1, 2], [3]]
        xs.__setitem__(0, [4, 5, 6])
        last = xs.pop()
        last.append(7)
        first = xs.pop()
        xs.discard_empty()
        return len(first) + len(last)

    run_int_fn(main, 5)


def test_empty_linear_disposal(run_int_fn):
    @guppy
    def main() -> int:
        xs: list[qubit] = []
        xs.discard_empty()
        return 42

    run_int_fn(main, 42)


def test_linear_push_pop_and_disposal(run_int_fn):
    @guppy
    def main() -> int:
        xs = [qubit()]
        q = xs.pop()
        xs.discard_empty()
        discard(q)
        return 42

    run_int_fn(main, 42, num_qubits=1)


def test_nonempty_disposal_panics(run_int_fn):
    @guppy
    def main() -> int:
        xs = [1]
        xs.discard_empty()
        return 42

    with pytest.raises(EmulatorError, match=r"empty|nonempty"):
        run_int_fn(main, 42)


def test_insert_at_end_and_into_empty(run_int_fn):
    @guppy
    def main() -> int:
        xs: list[int] = []
        insert(xs, 0, 7)
        length = len(xs)
        insert(xs, length, 42)
        result = xs.pop() + xs.pop()
        xs.discard_empty()
        return result

    run_int_fn(main, 49)


def test_failed_insert_panics(run_int_fn):
    @guppy
    def main() -> int:
        xs = [7]
        insert(xs, 3, 42)
        return xs.pop()

    with pytest.raises(EmulatorError, match="List index out of bounds"):
        run_int_fn(main, 7)


def test_list_array_cleanup_with_moved_out_slot(run_int_fn):
    @guppy
    def main() -> int:
        xs = array([1, 2], [3])
        ys = xs.__getitem__(0)
        ys.append(4)
        return len(ys)

    run_int_fn(main, 3)


def test_direct_linear_iteration(run_int_fn):
    @guppy
    def main() -> int:
        xs = [qubit(), qubit()]
        count = 0
        for q in xs:
            discard(q)
            count += 1
        return count

    run_int_fn(main, 2, num_qubits=2)


def test_linear_set_returns_prior_element(run_int_fn):
    @guppy
    def main() -> int:
        old = qubit()
        quantum_x(old)
        xs = [old]
        previous = xs.swap(0, qubit())
        result = 1 if measure(previous).read() else 0
        remaining = xs.pop()
        result += 2 if measure(remaining).read() else 0
        xs.discard_empty()
        return result

    run_int_fn(main, 1, num_qubits=2)


def test_failed_linear_set_returns_supplied_element(run_int_fn):
    @guppy
    def main() -> int:
        old = qubit()
        quantum_x(old)
        xs = [old]
        supplied = failed_set_for_test(xs, 3, qubit())
        result = 1 if measure(supplied).read() else 0
        remaining = xs.pop()
        result += 2 if measure(remaining).read() else 0
        xs.discard_empty()
        return result

    run_int_fn(main, 2, num_qubits=2)


def test_direct_linear_insert_order(run_int_fn):
    @guppy
    def main() -> int:
        xs: list[qubit] = []
        first = qubit()
        quantum_x(first)
        insert_qubit_for_test(xs, 0, first)
        length = len(xs)
        insert_qubit_for_test(xs, length, qubit())
        last = xs.pop()
        first = xs.pop()
        result = 1 if measure(first).read() else 0
        result += 2 if measure(last).read() else 0
        xs.discard_empty()
        return result

    run_int_fn(main, 1, num_qubits=2)


def test_swap_out_of_bounds_panics(run_int_fn):
    @guppy
    def main() -> int:
        xs = [1]
        return xs.swap(3, 42)

    with pytest.raises(EmulatorError, match="List index out of bounds"):
        run_int_fn(main, 42)
