from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.emulator import EmulatorError
from guppylang.std.option import Option, nothing, some

from typing import TYPE_CHECKING
import pytest

if TYPE_CHECKING:
    from guppylang.std.quantum import qubit


def test_none(run_int_fn):
    @guppy
    @no_type_check
    def main() -> int:
        x: Option[int] = nothing()
        is_none = 10 if x.is_nothing() else 0
        is_some = 1 if x.is_some() else 0
        return is_none + is_some

    run_int_fn(main, expected=10)


def test_some_unwrap(run_int_fn):
    @guppy
    @no_type_check
    def main() -> int:
        x: Option[int] = some(42)
        is_none = 1 if x.is_nothing() else 0
        is_some = x.unwrap() if x.is_some() else 0
        return is_none + is_some

    run_int_fn(main, expected=42)


def test_nothing_unwrap(run_int_fn):
    @guppy
    @no_type_check
    def main() -> int:
        x: Option[qubit] = nothing()
        x.unwrap_nothing()  # linearity error without this line
        return 1

    run_int_fn(main, expected=1)


def test_take(run_int_fn):
    @guppy
    @no_type_check
    def main() -> int:
        x: Option[int] = some(42)
        y = x.take().unwrap()
        is_none = 1 if x.is_nothing() else 0
        return y + is_none

    run_int_fn(main, expected=43)


def test_comptime_create(run_int_fn):
    @guppy.comptime
    def positive(i: int) -> Option[int]:
        return some(i)

    @guppy
    def main() -> int:
        return positive(42).unwrap()

    run_int_fn(main, 42)


def test_comptime_unwrap(run_int_fn):
    @guppy
    def positive(i: int) -> Option[int]:
        return some(i) if i > 0 else nothing[int]()

    @guppy.comptime
    def main(i: int) -> int:
        return positive(i).unwrap()

    run_int_fn(main, 42, args=[42])
    with pytest.raises(EmulatorError, match=r"Option.unwrap: value is `Nothing`"):
        run_int_fn(main, 42, args=[-1])


def test_comptime_argument(run_int_fn):
    @guppy.comptime
    def foo(o: Option[int]) -> Option[int]:
        res = o.take()
        o.unwrap_nothing()
        return res

    @guppy
    def main(i: int) -> int:
        if i > 0:
            return foo(some(i)).unwrap()
        else:
            foo(nothing()).unwrap_nothing()
            return 0

    run_int_fn(main, 42, args=[42])
    run_int_fn(main, 0, args=[-1])
