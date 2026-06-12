from guppylang.decorator import guppy
from guppylang.std.array import array

n = guppy.nat_var("n")


@guppy
def main(xs: array[int, n]) -> None:
    x, _ = xs


main.check()
