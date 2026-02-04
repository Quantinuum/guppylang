from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q: qubit) -> None: ...


@guppy
def test() -> None:
   foo(qubit())


test.compile()
