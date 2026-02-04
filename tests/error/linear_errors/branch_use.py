from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def new_qubit() -> qubit:
    ...


@guppy.declare
def measure(q: qubit @owned) -> bool:
    ...


@guppy
def foo(b: bool) -> bool:
    q = new_qubit()
    if b:
        return measure(q)
    return False


foo.compile()
