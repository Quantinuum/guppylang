from guppylang import guppy
from guppylang.std.builtins import array


n = guppy.nat_var("n")


@guppy
def foo(xs: array[int, n]) -> int:
    a, *bs = xs
    return a


foo.compile()
