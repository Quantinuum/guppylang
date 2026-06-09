from guppylang import guppy, qubit
from guppylang.std.builtins import owned


@guppy.declare(unitary=True)
def uni_discard(q: qubit @owned) -> None: ...


@guppy(unitary=True)
def test() -> None:
    p = qubit()
    uni_discard(p)

test.compile()
