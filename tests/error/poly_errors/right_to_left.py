from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo() -> T:
    ...


@guppy.declare
def bar(x: T, y: T) -> None:
    ...


@guppy
def main() -> None:
    bar(foo(), 42)


main.compile()
