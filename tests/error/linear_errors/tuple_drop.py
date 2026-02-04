from tests.util import compile_guppy
from guppylang.std.quantum import qubit

@compile_guppy
def foo() -> qubit:
    return (1, qubit(), qubit())[1]
