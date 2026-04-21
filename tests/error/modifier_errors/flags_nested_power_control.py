from guppylang.decorator import guppy
from guppylang.std.builtins import control, power
from guppylang.std.quantum import qubit


@guppy(power=True)
def foo(q: qubit) -> None:
    pass


@guppy
def test(ctrl: qubit) -> None:
    q = qubit()
    with power(2):
        with control(ctrl):
            foo(q)


test.compile()
