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
