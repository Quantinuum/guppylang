from guppylang import guppy
from guppylang.std.builtins import nat, comptime, array


@guppy.declare
def foo(n: nat @comptime, xs: "array[int, n]") -> None: ...


@guppy
def bar(n: nat @comptime, m: nat @comptime) -> None:
    foo(n, array(i for i in range(m)))


@guppy
def main() -> None:
    bar(42, 42)  # This succeeds
    bar(42, 43)  # This fails


main.compile_function()
