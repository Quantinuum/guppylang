from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.option import Option, nothing, some
from guppylang.std.quantum import qubit  # noqa: TC002


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
