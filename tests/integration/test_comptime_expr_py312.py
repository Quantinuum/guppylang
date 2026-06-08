"""Tests for using Python expressions in Guppy functions with generics only introduced
in Python 3.12."""

from guppylang.decorator import guppy
from guppylang.std.builtins import comptime, nat


def test_generic(validate):
    @guppy
    def foo[n: nat]() -> None:
        pass

    N = 100

    @guppy
    def main() -> None:
        foo[comptime(N)]()

    validate(main.compile_function())


def test_use_generic(run_int_fn):
    n = 0  # Test that this n is not captured

    @guppy
    def foo[n: nat, m: nat]() -> int:
        return int(comptime(n - m + 1))

    @guppy
    def main() -> int:
        return foo[20, 10]()

    run_int_fn(main, 11)
