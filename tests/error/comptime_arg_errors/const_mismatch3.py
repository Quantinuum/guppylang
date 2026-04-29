from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def foo(n: nat @comptime) -> None:
    pass


@guppy
def bar(n: nat @ comptime, m: nat @ comptime) -> None:
    foo[n](m)


@guppy
def main() -> None:
    # This fails the parametric check, even though the monomorphisation would be ok:
    bar(42, 42)


main.compile_function()
