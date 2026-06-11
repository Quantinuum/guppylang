"""Subscript indexing in dagger and control context"""

from pathlib import Path
from sys import argv
import sys

from guppylang import array, guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard_array
from guppylang.std.quantum import h, s

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    controller = array(qubit())
    array_qubits: array[qubit, 2] = array(qubit(), qubit())
    h(controller[0])
    with dagger:
        with control(controller[0]):
            s(array_qubits[1])
            h(array_qubits[1])

    state_result("r", controller[0], array_qubits[0], array_qubits[1])
    discard_array(array_qubits)
    discard_array(controller)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
