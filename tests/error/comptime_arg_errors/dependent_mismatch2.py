from guppylang import guppy
from guppylang.std.builtins import nat, comptime, array


@guppy.declare
def foo(n: nat @comptime, xs: "array[int, n]") -> None: ...


@guppy
def bar(n: nat @comptime, m: nat @comptime) -> None:
    foo(n, array(i for i in range(m)))


@guppy
def main() -> None:
    # This fails the parametric check, even though the monomorphisation would be ok:
    bar(42, 42)


main.compile_function()
