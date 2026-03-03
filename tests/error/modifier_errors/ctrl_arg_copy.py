from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, owned


@guppy.declare
def discard(q: qubit @ owned) -> None: ...


@guppy.declare(control=True)
def use(q: qubit) -> None: ...


@guppy
def test() -> None:
    q = qubit()
    with control(q):
        use(q)
    discard(q)


test.compile()
