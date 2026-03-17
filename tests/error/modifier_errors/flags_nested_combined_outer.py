from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy(power=True)
def foo(q: qubit) -> None:
    pass


@guppy
def test(ctrl: qubit) -> None:
    q = qubit()
    with control(ctrl), dagger:
        with power(2):
            foo(q)


test.compile()
