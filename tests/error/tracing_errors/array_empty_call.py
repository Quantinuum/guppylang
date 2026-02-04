from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy.declare
def foo(xs: array[int, 0]) -> None: ...


@guppy.comptime
def test(xs: array[int, 0]) -> None:
    foo(xs)  # This works
    foo([])  # But we currently cannot infer the type here


test.compile()
