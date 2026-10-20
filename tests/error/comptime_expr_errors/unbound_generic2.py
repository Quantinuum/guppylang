from guppylang import guppy, array
from guppylang.std.builtins import comptime

n = guppy.nat_var("n")


@guppy
def main(xs: array[int, "comptime(n + 1)"]) -> None:
    pass


main.compile()
