from guppylang import guppy
from guppylang.std.builtins import nat, comptime, array


@guppy.declare
def foo(n: nat @comptime, xs: "array[int, n]") -> None: ...


@guppy
def main(n: nat @comptime, m: nat @comptime) -> None:
    foo(n, array(i for i in range(m)))


main.compile_function()
