from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, cx


@guppy.comptime
def test(q: qubit) -> None:
    cx(q, q)


test.compile()
