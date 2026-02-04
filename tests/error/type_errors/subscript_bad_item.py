from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def foo(xs: array[int, 42]) -> int:
    return xs[1.0]


foo.compile()
