from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def new_qubit() -> qubit:
    ...


@guppy
def foo(b: bool) -> int:
    if b:
        q = new_qubit()
    else:
        q = new_qubit()
    return 42


foo.compile()
