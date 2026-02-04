from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def foo(n: nat @comptime) -> nat:
    return n


@guppy
def main(b: bool) -> nat:
    return foo(nat(1) if b else nat(2))


main.compile_function()
