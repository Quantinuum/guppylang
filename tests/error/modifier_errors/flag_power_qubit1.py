from guppylang import qubit, guppy
from guppylang.std.builtins import owned, power

@guppy.declare
def uni_discard(q: qubit @owned) -> None: ...

@guppy
def test() -> None:
    with power(2):
        p = qubit()
        uni_discard(p)


test.compile()
