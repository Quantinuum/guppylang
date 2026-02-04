from guppylang import array
from guppylang.decorator import guppy

n = guppy.nat_var("n")


@guppy.comptime
def test(xs: array[int, n]) -> None:
    pass


test.compile()
