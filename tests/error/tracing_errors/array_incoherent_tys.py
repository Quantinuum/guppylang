from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy.comptime
def test(xs: array[int, 10]) -> None:
    xs[1] = 1.0


test.compile()
