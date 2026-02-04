from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy
def test(q: qubit) -> qubit:
    r = q
    q = qubit()
    return r


test.compile()
