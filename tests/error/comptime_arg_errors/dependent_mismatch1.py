from guppylang import guppy
from guppylang.std.builtins import nat, comptime, array


@guppy.declare
def foo(n: nat @comptime, xs: "array[int, n]") -> None: ...


@guppy
def main() -> None:
    foo(3, array(1, 2))


main.compile()
