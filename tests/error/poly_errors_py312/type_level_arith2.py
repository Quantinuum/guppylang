from guppylang import guppy, comptime
from guppylang.std.array import array
from guppylang.std.num import nat


@guppy
def foo[n: nat]() -> array[int, "comptime(2 * n)"]:
    # This is wrong, but only for certain values of n:
    return array(0 for _ in range(comptime(n ** 2)))


@guppy
def main() -> None:
    foo[0]()  # Ok since 2*0 = 0^2
    foo[2]()  # Ok since 2*2 = 2^2
    foo[1]()  # Monomorphisation fails


main.compile()
