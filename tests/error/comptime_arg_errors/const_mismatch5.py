from guppylang import guppy
from guppylang.std.builtins import comptime

T = guppy.type_var("T", copyable=True, droppable=True)


@guppy
def foo(x: T @ comptime) -> None:
    pass


@guppy
def bar(x: T @ comptime, y: T @ comptime) -> None:
    foo[T, x](y)


@guppy
def main() -> None:
    bar(42, 42)      # This succeeds
    bar(True, True)  # This succeeds
    bar(42, 43)      # This fails


main.compile()
