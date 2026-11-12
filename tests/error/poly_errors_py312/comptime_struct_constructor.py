from guppylang import comptime, guppy
from guppylang.std.array import array
from guppylang.std.num import nat


@guppy.struct
class Buffer[n: nat]:
    xs: array[int, "comptime(n + 1)"]


@guppy
def make[n: nat]() -> Buffer[n]:
    # The constructor argument has the right size only when n = 1.
    return Buffer[n](array(0 for _ in range(comptime(2 * n))))


@guppy
def main() -> None:
    make[1]()
    make[2]()


main.compile()
