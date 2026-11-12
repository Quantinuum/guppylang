from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.lang import Copy
from guppylang.std.num import nat


@guppy.declare
def foo[T: Copy, n: nat](xs: array[T, n]) -> array[T, "comptime(2 * n)"]:
    ...


@guppy
def main() -> array[int, 8]:
    return foo(array(1, 2, 3))


main.compile()
