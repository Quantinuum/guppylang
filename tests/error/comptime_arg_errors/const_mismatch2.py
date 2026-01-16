from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def foo(n: nat @comptime) -> None:
    pass


@guppy
def bar(n: nat @ comptime) -> None:
    foo[n](42)


@guppy
def main() -> None:
    bar(42)  # This succeeds
    bar(43)  # This fails


main.compile_function()
