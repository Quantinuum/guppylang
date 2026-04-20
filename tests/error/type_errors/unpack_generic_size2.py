from guppylang import guppy
from guppylang.std.builtins import array


n = guppy.nat_var("n")


@guppy
def foo(_xs: array[int, n]) -> int:
    a, *bs = range(n)
    return a


foo.compile()
