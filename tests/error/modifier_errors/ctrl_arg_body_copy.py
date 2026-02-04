from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, owned


@guppy.declare
def discard(q: qubit @ owned) -> None: ...


@guppy
def test() -> None:
    q = qubit()
    with control(q, q):
        pass
    discard(q)


test.compile()
