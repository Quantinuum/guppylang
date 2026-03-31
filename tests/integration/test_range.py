import builtins

from guppylang.decorator import guppy
from guppylang.std.builtins import range, SizedIter, py
from guppylang.std.iter import Range


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
    n = 10

    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(py(n))

    validate(negative.compile_function())


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
