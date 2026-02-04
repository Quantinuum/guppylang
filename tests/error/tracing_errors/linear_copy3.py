from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, cx


@guppy.comptime
def test() -> qubit:
    q = qubit()
    cx(q, q)
    return q


test.compile()
