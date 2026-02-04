from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def foo(xs: array[array[int, 10], 20]) -> array[int, 10]:
    return xs[0]

foo.compile()
