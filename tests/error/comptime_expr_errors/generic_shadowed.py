from guppylang import guppy
from guppylang.std.builtins import array, comptime

n = guppy.nat_var("n")


@guppy
def foo(xs: array[int, n]) -> None:
    n = 42
    comptime(n)


@guppy
def main() -> None:
    foo(array(1, 2, 3))


main.compile()
