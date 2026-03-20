from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def discard_array(a: array[qubit, 1] @ owned) -> None: ...


@guppy
def test() -> None:
    x = array(qubit())
    y = array(qubit())
    with control(x, y):
        pass
    discard_array(x)
    discard_array(y)


test.compile()
