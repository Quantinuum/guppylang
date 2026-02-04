from guppylang import guppy
from guppylang.std.builtins import comptime, nat, array

n = guppy.nat_var("n")


@guppy
def main(xs: array[int, n], n: nat @comptime) -> None:
    pass


main.compile_function()
