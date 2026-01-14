from guppylang import guppy
from guppylang.std.builtins import array


n = guppy.nat_var("n")


@guppy
def foo(xs: array[int, n]) -> int:
    a, *bs = xs
    return a


@guppy
def main() -> None:
    foo(array(1, 2, 3))  # This succeeds
    foo(array())  # This fails


main.compile()
