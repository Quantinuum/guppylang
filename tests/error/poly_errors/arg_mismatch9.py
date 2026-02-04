from guppylang.decorator import guppy

S = guppy.type_var("S")
T = guppy.type_var("T")


@guppy.declare
def foo(x: S, y: T) -> None:
    ...


@guppy
def main(x: int, y: float) -> None:
    foo[float, int](x, y)


main.compile_function()
