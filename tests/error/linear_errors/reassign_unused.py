from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def new_qubit() -> qubit:
    ...


@guppy
def foo(q: qubit @owned) -> qubit:
    q = new_qubit()
    return q


foo.compile()
