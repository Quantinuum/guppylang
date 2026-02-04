from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.array import array


@guppy.declare
def foo(a: array[int, 3], b: array[int, 3]) -> None: ...


@guppy
def test() -> None:
    q = qubit()
    with control(q):
        xs = array(1, 2, 3)
        foo(xs, xs)


test.compile()
