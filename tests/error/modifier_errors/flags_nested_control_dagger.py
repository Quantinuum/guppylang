from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy(control=True)
def foo(q: qubit) -> None:
    pass


@guppy
def test(ctrl: qubit) -> None:
    q = qubit()
    with control(ctrl):
        with dagger:
            foo(q)


test.compile()
