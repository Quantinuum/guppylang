from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def foo(n: nat @comptime) -> None:
    pass


@guppy
def main(n: nat @ comptime) -> None:
    foo[42](n)


main.compile_function()
