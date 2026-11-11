from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.num import nat


@guppy.struct
class Buffer[n: nat]:
    xs: array[int, "comptime(n + 1)"]


@guppy
def main() -> None:
    a = Buffer[1](array(1, 2))
    b = Buffer[2](array(3, 4, 5))
    a.xs = b.xs


main.compile()
