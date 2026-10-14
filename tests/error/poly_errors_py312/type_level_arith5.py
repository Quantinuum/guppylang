from guppylang import guppy, comptime
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.num import nat


@guppy
def foo[n: nat](xs: array[int, "comptime(n + 1)"]) -> None:
    pass


@guppy
def main() -> None:
    foo[0](array(1))
    foo[1](array(1, 2))
    foo[2](array(1, 2))


main.compile()
