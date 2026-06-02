from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, measure


@guppy.comptime
def test(q: qubit) -> None:
    measure(q)


test.compile()
