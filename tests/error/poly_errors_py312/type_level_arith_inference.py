from guppylang import guppy, comptime
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.num import nat


@guppy
def tail[n: nat](xs: array[int, "comptime(n + 1)"] @ owned) -> array[int, n]:
    _, *ys = xs
    return ys

@guppy
def main() -> None:
    tail(array(1, 2, 3))


main.compile()
