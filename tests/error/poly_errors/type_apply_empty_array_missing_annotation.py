from guppylang.decorator import guppy
from guppylang.std.builtins import array

T = guppy.type_var("T")
n = guppy.nat_var("n")

@guppy.declare
def foo(xs: array[T, n]) -> array[T, n]: ...

@guppy
def main() -> None:
    xs = foo(array())

main.compile()
