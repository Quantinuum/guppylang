from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.std.qsystem import measure


@guppy.comptime
def test() -> int:
    q = qubit()
    if measure(q):
        return 1
    return 0


test.compile()
