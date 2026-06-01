from guppylang.decorator import guppy
from guppylang.std.builtins import dagger, power
from guppylang.std.quantum import qubit


@guppy.declare(power=True)
def foo(q: qubit) -> None: ...


@guppy
def test(q: qubit) -> None:
    with dagger, dagger:
        with power(2):
            with dagger:
                foo(q)


test.compile()
