from guppylang import qubit
from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int
    q: qubit


@guppy.comptime
def test(s: S) -> None:
    s.x = 1.0


test.compile()
