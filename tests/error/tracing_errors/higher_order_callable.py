from collections.abc import Callable

from guppylang.decorator import guppy

S = guppy.type_var("S")
T = guppy.type_var("T")


@guppy.comptime
def call(f: Callable[[S], T], x: S) -> T:
    # Higher-order comptime functions not supported yet :/
    return f(x)


@guppy
def foo(x: int) -> int:
    return x + 1


@guppy
def bar(x: bool) -> float:
    return 1.0 if x else 1.5


@guppy.comptime
def main() -> float:
    return call(foo, 42) + call(bar, True)


main.compile()
