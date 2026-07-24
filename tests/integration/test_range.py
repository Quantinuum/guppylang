import builtins

import pytest

from guppylang.decorator import guppy
from guppylang.emulator import EmulatorError
from guppylang.std.builtins import output, range
from guppylang.std.iter import Range, SizedIter


def test_range(run_int_fn):
    @guppy
    def stop(stop: int) -> int:
        total = 0
        for x in range(stop):
            total += x + 100  # Make the initial 0 obvious
        return total

    @guppy
    def start(start: int, stop: int) -> int:
        total = 0
        for x in range(start, stop):
            total += x + 100
        return total

    @guppy
    def step(start: int, stop: int, step: int) -> int:
        total = 0
        for x in range(start, stop, step):
            total += x + 100
        return total

    def expected(r) -> int:
        return sum(x + 100 for x in r)

    run_int_fn(stop, args=[5], expected=expected(builtins.range(5)))
    run_int_fn(stop, args=[-3], expected=expected(builtins.range(-3)))
    run_int_fn(start, args=[2, 7], expected=expected(builtins.range(2, 7)))
    run_int_fn(start, args=[-2, 5], expected=expected(builtins.range(-2, 5)))
    run_int_fn(step, args=[1, 5, 2], expected=expected(builtins.range(1, 5, 2)))
    run_int_fn(step, args=[5, -2, -1], expected=expected(builtins.range(5, -2, -1)))


def test_static_size(validate):
    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(10)

    validate(negative.compile_function())


def test_py_size(validate):
    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(10)

    validate(negative.compile_function())


def test_py_size_var(validate):
    """Python variable (not literal) used as sized range argument."""
    n = 10

    @guppy
    def foo() -> SizedIter[Range, 10]:
        return range(n)

    validate(foo.compile_function())


def test_static_generic_size(validate):
    n = guppy.nat_var("n")

    @guppy
    def foo() -> SizedIter[Range, n]:
        return range(n)

    @guppy
    def main() -> None:
        r1: SizedIter[Range, 10] = foo()
        r2: SizedIter[Range, 0] = foo()

    validate(main.compile_function())


def test_range_reverse(run_int_fn):
    """Reversing a range iterates the same elements as `reversed(range(...))`."""

    @guppy
    def main(start: int, stop: int, step: int) -> int:
        total = 0
        r = range(start, stop, step)
        r.reverse_in_place()
        for x in r:
            total += x + 100  # Make the initial 0 obvious
        return total

    def expected(a: int, b: int, s: int) -> int:
        return sum(x + 100 for x in reversed(builtins.range(a, b, s)))

    # Positive steps (including one that doesn't divide the span evenly)
    run_int_fn(main, args=[0, 5, 1], expected=expected(0, 5, 1))
    run_int_fn(main, args=[1, 5, 2], expected=expected(1, 5, 2))
    run_int_fn(main, args=[1, 5, 3], expected=expected(1, 5, 3))
    run_int_fn(main, args=[2, 7, 1], expected=expected(2, 7, 1))
    run_int_fn(main, args=[-2, 5, 1], expected=expected(-2, 5, 1))
    run_int_fn(main, args=[0, 10, 3], expected=expected(0, 10, 3))

    # Negative steps
    run_int_fn(main, args=[5, 0, -1], expected=expected(5, 0, -1))
    run_int_fn(main, args=[6, 0, -2], expected=expected(6, 0, -2))
    run_int_fn(main, args=[5, -2, -1], expected=expected(5, -2, -1))
    run_int_fn(main, args=[10, 0, -3], expected=expected(10, 0, -3))
    run_int_fn(main, args=[2, 5, -1], expected=expected(2, 5, -1))

    # Empty ranges (reverse of an empty iterator is still empty)
    run_int_fn(main, args=[5, 2, 1], expected=expected(5, 2, 1))
    run_int_fn(main, args=[0, 0, 1], expected=expected(0, 0, 1))
    run_int_fn(main, args=[5, 5, 1], expected=expected(5, 5, 1))
    run_int_fn(main, args=[7, 7, 5], expected=expected(7, 7, 5))
    run_int_fn(main, args=[3, 3, -2], expected=expected(3, 3, -2))


def test_range_reverse_validate(validate):
    """The reversed-range loop compiles to a well-formed HUGR."""

    @guppy
    def main(start: int, stop: int, step: int) -> int:
        total = 0
        r = range(start, stop, step)
        r.reverse_in_place()
        for x in r:
            total += x
        return total

    validate(main.compile_function())


def test_range_reverse_twice(run_int_fn):
    """Reversing twice restores the original iteration order (idempotence)."""

    @guppy
    def main(start: int, stop: int, step: int) -> int:
        total = 0
        r = range(start, stop, step)
        r.reverse_in_place()
        r.reverse_in_place()
        for x in r:
            total += x + 100
        return total

    def expected(a: int, b: int, s: int) -> int:
        return sum(x + 100 for x in builtins.range(a, b, s))

    run_int_fn(main, args=[1, 5, 2], expected=expected(1, 5, 2))
    run_int_fn(main, args=[5, 0, -1], expected=expected(5, 0, -1))
    run_int_fn(main, args=[0, 10, 3], expected=expected(0, 10, 3))
    run_int_fn(main, args=[10, 0, -3], expected=expected(10, 0, -3))
    run_int_fn(main, args=[5, 2, 1], expected=expected(5, 2, 1))


def test_range_zero_step_panic() -> None:
    """Constructing `range(a, b, 0)` panics at runtime instead of hanging."""

    @guppy
    def main() -> None:
        total = 0
        for x in range(1, 5, 0):
            total += x
        output("_test_output", total)

    with pytest.raises(EmulatorError, match=r"range\(\) arg 3 must not be zero"):
        main.emulator(n_qubits=0).stabilizer_sim().with_seed(42).run()


def test_range_reverse_zero_step_panic() -> None:
    """`reverse_in_place` on a zero-step range panics instead of hanging.

    The public `range()` constructor already rejects `step == 0`, so we reach a
    zero-step state by constructing `Range` directly.
    """

    @guppy
    def main() -> None:
        r = Range(1, 5, 0)
        r.reverse_in_place()
        output("_test_output", 0)

    with pytest.raises(EmulatorError, match=r"range.reverse_in_place: step is zero"):
        main.emulator(n_qubits=0).stabilizer_sim().with_seed(42).run()
