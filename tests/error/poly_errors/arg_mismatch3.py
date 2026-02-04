from guppylang.decorator import guppy
from guppylang.std.builtins import array

n = guppy.nat_var("n")


@guppy.declare
def foo(x: array[int, n], y: array[int, n]) -> None:
    ...


@guppy
def main(x: array[int, 42], y: array[int, 43]) -> None:
    foo(x, y)


main.compile_function()
