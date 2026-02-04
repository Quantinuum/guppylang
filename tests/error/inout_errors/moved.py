from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q1: qubit) -> None: ...


@guppy.declare
def use(q: qubit @owned) -> None: ...


@guppy
def test(q: qubit) -> None:
    foo(q)
    use(q)


test.compile()
