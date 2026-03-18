from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, cx


@guppy
def foo() -> None:
    qubits = array((qubit() for _ in range(2)))
    cx(qubits[0], qubits[0])


foo.compile()
