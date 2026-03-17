from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy(dagger=True)
def foo(q: qubit) -> None:
    pass


@guppy
def test() -> None:
    q = qubit()
    with dagger:
        with power(2):
            foo(q)


test.compile()
