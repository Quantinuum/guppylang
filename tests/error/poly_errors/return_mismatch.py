from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo() -> tuple[T, T]:
    ...


@guppy
def main() -> None:
    x: bool = foo()


main.compile()
