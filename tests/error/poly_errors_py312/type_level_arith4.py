from guppylang import guppy, comptime
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.num import nat


@guppy
def tail[T](n: nat @ comptime, xs: array[T, "comptime(n + 1)"] @ owned) -> "array[T, n]":
    _, *ys = xs
    return ys

@guppy
def main() -> None:
    tail(0, array())


main.compile()
