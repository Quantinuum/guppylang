from guppylang.decorator import guppy

S = guppy.type_var("S")
T = guppy.type_var("T")
U = guppy.type_var("U")


@guppy.declare
def foo(x: int) -> None:
    ...


@guppy
def main() -> None:
    foo[int](0)


main.compile()
