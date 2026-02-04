from guppylang.decorator import guppy
from guppylang.std.builtins import array

n = guppy.nat_var("n")


@guppy.declare
def foo(x: array[int, n]) -> None:
    ...


@guppy
def main(xs: array[int, 42]) -> None:
    foo[43](xs)


main.compile_function()
