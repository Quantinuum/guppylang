from guppylang.decorator import guppy

S = guppy.type_var("S")
T = guppy.type_var("T")
U = guppy.type_var("U")


@guppy.declare
def foo(x: S, y: T, z: U) -> None:
    ...


@guppy
def main() -> None:
    foo[int, int]


main.compile()
