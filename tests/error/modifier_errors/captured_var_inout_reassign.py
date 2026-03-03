from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare(dagger=True)
def use(q: qubit) -> None: ...


@guppy
def test() -> None:
    a = qubit()
    with dagger:
        use(a)


test.compile()
