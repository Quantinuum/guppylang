from guppylang.decorator import guppy
from guppylang.std.lang import comptime

T = guppy.type_var("T", copyable=True, droppable=True)


@guppy
def foo(x: T, y: T @ comptime) -> None:
    pass


@guppy
def main() -> None:
    foo(42, True)


main.compile()
