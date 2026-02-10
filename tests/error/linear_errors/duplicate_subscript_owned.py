from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit, h


@guppy
def mixed_ownership(q1: qubit, q2: qubit @owned) -> tuple[qubit, qubit]:
    q1 = h(q1)
    return q1, q2


@guppy
def foo() -> None:
    qubits = array((qubit() for _ in range(3)))

    # Compile time error: The same qubit cannot be used with different
    # ownership modes simultaneously due to required linearity.
    q1, q2 = mixed_ownership(qubits[0], qubits[0])


foo.compile()
