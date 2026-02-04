from guppylang.decorator import guppy

S = guppy.type_var("S")
T = guppy.type_var("T")
U = guppy.type_var("U")


@guppy.declare
def foo(x: int) -> None:
    ...


@guppy
def main() -> None:
    f = foo
    f[int](0)


main.compile()
