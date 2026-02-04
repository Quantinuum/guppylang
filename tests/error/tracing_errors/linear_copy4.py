from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, h, measure


@guppy.comptime
def test() -> None:
    q = qubit()
    measure(q)
    h(q)


test.compile()
