from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q: qubit) -> None: ...


@guppy
def test(ctrl: qubit) -> None:
    q = qubit()
    with dagger:
        with control(ctrl):
            with power(2):
                foo(q)


test.compile()
