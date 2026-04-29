from guppylang import guppy, qubit
from guppylang.std.builtins import dagger, owned

@guppy.declare(unitary=True)
def uni_discard(q: qubit @owned) -> None: ...

@guppy
def test() -> None:
    with dagger:
        p = qubit()
        uni_discard(p)


test.compile()
