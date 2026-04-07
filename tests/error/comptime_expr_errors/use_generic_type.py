from guppylang import guppy
from guppylang.std.builtins import comptime

T = guppy.type_var("T")


@guppy
def foo(x: T) -> None:
    comptime(T)


@guppy
def main() -> None:
    foo(42)


main.compile()
