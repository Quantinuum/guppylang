from guppylang import guppy
from guppylang.std.builtins import comptime, nat

T = guppy.type_var("T")


@guppy
def foo(x: T, n: nat @comptime) -> None:
    pass


@guppy
def main() -> None:
    foo[int](42, 43)


main.compile()
