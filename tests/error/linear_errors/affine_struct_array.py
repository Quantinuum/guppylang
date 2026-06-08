from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy
def foo(xs: array[MyStruct, 20]) -> MyStruct:
    return xs[0]

foo.compile()
