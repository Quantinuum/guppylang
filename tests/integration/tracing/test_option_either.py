import pytest

from guppylang.decorator import guppy
from guppylang.emulator import EmulatorError
from guppylang.std.either import Either, left, right
from guppylang.std.option import Option, some, nothing


def test_create_option(run_int_fn):
    @guppy.comptime
    def positive(i: int) -> Option[int]:
        return some(i)

    @guppy
    def main() -> int:
        return positive(42).unwrap()

    run_int_fn(main, 42)


def test_unwrap_option(run_int_fn):
    @guppy
    def positive(i: int) -> Option[int]:
        return some(i) if i > 0 else nothing[int]()

    @guppy.comptime
    def main(i: int) -> int:
        return positive(i).unwrap()

    run_int_fn(main, 42, args=[42])
    with pytest.raises(EmulatorError):
        run_int_fn(main, 42, args=[-1])


def test_argument_option(validate):
    @guppy.comptime
    def foo(o: Option[int]) -> Option[int]:
        res = o.take()
        o.unwrap_nothing()
        return res

    @guppy
    def main(i: int) -> int:
        foo(nothing()).unwrap_nothing()
        return foo(some(i)).unwrap()

    validate(main.compile_function())


# Creating an 'Either' from comptime is not possible because
# one cannot (yet) explicitly specify the type of the *other* side


def test_unwrap_either(run_int_fn):
    @guppy
    def max(i: int, f: float) -> Either[int, float]:
        r: Either[int, float] = right(f)
        return left[int, float](i) if float(i) > f else r

    @guppy.comptime
    def main(i: int) -> int:
        return max(i, 3.14).unwrap_left()

    run_int_fn(main, 4, args=[4])
    with pytest.raises(EmulatorError):
        run_int_fn(main, 0xDEADBEEF, args=[3])


def test_either_into_left(run_int_fn):
    @guppy.comptime
    def foo(e: Either[int, float]) -> int:
        return e.try_into_left().unwrap()

    @guppy
    def main(i: int) -> int:
        r: Either[int, float] = right(3.14)
        e = (left[int, float](i)) if i > 0 else r
        return foo(e)

    run_int_fn(main, 3, args=[3])
    with pytest.raises(EmulatorError):
        run_int_fn(main, 0xDEADBEEF, args=[-3])
