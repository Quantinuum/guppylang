from guppylang import guppy
from guppylang.std.builtins import comptime

T = guppy.type_var("T", copyable=True, droppable=True)


@guppy
def foo(x: T @ comptime) -> None:
    pass


@guppy
def main(x: T @ comptime, y: T @ comptime) -> None:
    foo[T, x](y)


main.compile()
