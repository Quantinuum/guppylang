from guppylang import guppy
from guppylang.std.builtins import array


n = guppy.nat_var("n")


@guppy
def foo(_xs: array[int, n]) -> int:
    a, *bs = range(n)
    return a


@guppy
def main() -> None:
    foo(array(1, 2, 3))  # This succeeds
    foo(array())  # This fails


main.compile()
