from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy
def test(q: qubit) -> None:
    q = qubit()


test.compile()
