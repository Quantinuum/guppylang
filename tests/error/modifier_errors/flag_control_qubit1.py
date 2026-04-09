from guppylang import qubit, guppy
from guppylang.std.builtins import control, owned


@guppy.declare(unitary=True)
def uni_discard(q: qubit @owned) -> None: ...

@guppy
def test() -> None:
    q = qubit()
    with control(q):
        p = qubit()
        uni_discard(p)


test.compile()
