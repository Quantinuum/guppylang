from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def foo(n: nat @comptime) -> None:
    pass


@guppy
def main(n: nat @ comptime, m: nat @ comptime) -> None:
    foo[n](m)


main.compile_function()
