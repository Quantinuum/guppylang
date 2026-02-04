from typing import Callable

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(f: Callable[[T], T]) -> None:
    ...


@guppy.declare
def bar(x: T) -> T:
    ...


@guppy
def main() -> None:
    foo(bar)


main.compile()
