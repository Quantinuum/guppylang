from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy.comptime
def test(xs: array[int, 10]) -> None:
    xs.clear()
    for i in range(10):
        xs.append(float(i))


test.compile()
