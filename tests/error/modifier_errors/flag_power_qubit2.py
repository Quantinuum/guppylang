from guppylang import array, qubit, guppy
from guppylang.std.builtins import owned

@guppy.declare
def init_qubits() -> array[qubit, 2]: ...

@guppy.declare(unitary=True)
def uni_discard(q: array[qubit, 2] @owned) -> None: ...


@guppy(power=True)
def test() -> None:
    qp = init_qubits()
    uni_discard(qp)

test.compile()
