from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q: qubit) -> None: ...


@guppy
def test(q: qubit) -> None:
    with dagger, dagger, dagger:
        foo(q)


test.compile()
