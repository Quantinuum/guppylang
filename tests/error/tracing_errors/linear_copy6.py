from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.comptime
def test() -> tuple[qubit, qubit]:
    q = qubit()
    return q, q


test.compile()
