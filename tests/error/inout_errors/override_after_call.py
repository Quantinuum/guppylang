from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q1: qubit, q2: qubit @owned) -> qubit: ...


@guppy
def test(q1: qubit @owned, q2: qubit @owned) -> tuple[qubit, qubit]:
    q1 = foo(q1, q2)
    return q1, q2


test.compile()
