from guppylang import guppy, comptime
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.num import nat


@guppy
def tail[T, n: nat](xs: array[T, n] @ owned) -> array[T, "comptime(n - 1)"]:
    _, *ys = xs
    return ys


@guppy
def main() -> None:
    tail(array(1, 2, 3))  # Fine

    empty: array[int, 0] = array()
    tail(empty)  # Error


main.compile()
