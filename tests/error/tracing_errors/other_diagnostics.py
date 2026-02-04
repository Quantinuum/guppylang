"""Tests that non-comptime functions still get regular diagnostics, even if their
checking was invoked from a comptime function.

See https://github.com/quantinuum/guppylang/issues/1097
"""

from guppylang.decorator import guppy


@guppy
def foo() -> int:
    return


@guppy.comptime
def main() -> int:
    return foo()


main.compile()
