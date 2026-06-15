from guppylang.decorator import guppy
from guppylang.std.builtins import Fn

T = guppy.type_var("T")


@guppy.declare
def foo(f: Fn[[T], T]) -> None:
    ...


@guppy.declare
def bar(x: T) -> T:
    ...


@guppy
def main() -> None:
    foo(bar)


main.compile()
