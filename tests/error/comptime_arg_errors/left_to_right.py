from guppylang import guppy
from guppylang.std.builtins import nat, comptime, array


@guppy
def main(xs: "array[int, num]", num: nat @comptime) -> None:
    pass


main.compile_function()
