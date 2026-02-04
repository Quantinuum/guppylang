from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit, h

import guppylang
guppylang.enable_experimental_features()


@guppy
def swap_twice(q1: qubit, q2: qubit @owned) -> tuple[qubit, qubit]:
    """Takes one borrowed and one owned qubit."""
    q1 = h(q1)
    return q1, q2


@guppy
def foo() -> None:
    qubits = array((qubit() for _ in range(3)))
    # This should error - trying to borrow the same element while also consuming it
    q1, q2 = swap_twice(qubits[0], qubits[0])


foo.compile()
