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
    bar(42, 42)  # This succeeds
    bar(42, 43)  # This fails


main.compile_function()
