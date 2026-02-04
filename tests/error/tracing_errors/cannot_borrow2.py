from guppylang.decorator import guppy
from guppylang.std.mem import mem_swap


@guppy.comptime
def test() -> None:
    x = (1, 2)
    y = (3, 4)
    mem_swap(x, y)


test.compile()
