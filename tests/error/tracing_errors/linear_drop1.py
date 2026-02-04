from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.comptime
def test() -> None:
    q = qubit()


test.compile()
