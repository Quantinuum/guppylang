from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy
def test(q: qubit, b: bool) -> None:
    if b:
        q = qubit()


test.compile()
