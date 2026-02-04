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
def foo(i: int) -> bool:
    b = False
    while i > 0:
        q = new_qubit()
        if i % 10 == 0:
            break
        i -= 1
        b &= measure(q)
    return b


foo.compile()
