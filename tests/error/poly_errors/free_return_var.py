from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo() -> T:
    ...


@guppy
def main() -> None:
    x = foo()


main.compile()
