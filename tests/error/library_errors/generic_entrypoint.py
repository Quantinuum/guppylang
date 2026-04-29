from guppylang import guppy
from guppylang.std.array import array

T = guppy.type_var("T")

@guppy
def func(x: T) -> array[T, 3]:
    return array(x for _ in range(3))

lib = guppy.library(func).compile()
