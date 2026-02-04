from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(x: tuple[T, T]) -> None:
    ...


@guppy
def main() -> None:
    foo(False)


main.compile()
