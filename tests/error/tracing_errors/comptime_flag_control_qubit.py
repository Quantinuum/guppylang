from guppylang import qubit, guppy
from guppylang.std.builtins import array, owned


@guppy.declare
def init_qubits() -> array[qubit, 2]: ...


@guppy.declare(unitary=True)
def uni_discard(q: array[qubit, 2] @owned) -> None: ...


@guppy.comptime(control=True)
def test() -> None:
    p = init_qubits()
    uni_discard(p)


test.compile_function()
