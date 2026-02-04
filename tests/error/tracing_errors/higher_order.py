from collections.abc import Callable

from guppylang.decorator import guppy


@guppy.comptime
def test(f: Callable[[], int]) -> int:
    return f()


test.compile()
