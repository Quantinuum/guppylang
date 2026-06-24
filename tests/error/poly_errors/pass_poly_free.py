from guppylang.decorator import guppy
from guppylang.std.builtins import Function

T = guppy.type_var("T")


@guppy.declare
def foo(f: Function[[T], T]) -> None:
    ...


@guppy.declare
def bar(x: T) -> T:
    ...


@guppy
def main() -> None:
    foo(bar)


main.compile()
