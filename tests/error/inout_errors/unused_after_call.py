from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q: qubit) -> None: ...


@guppy
def test(q: qubit @owned) -> None:
   foo(q)


test.compile()
