"""Subscript indexing in dagger context"""

from pathlib import Path
from sys import argv
import sys

from guppylang import array, guppy
from guppylang.std.builtins import dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard_array
from guppylang.std.quantum import h, s

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    array_qubits: array[qubit, 2] = array(qubit(), qubit())

    with dagger:
        s(array_qubits[1])
        h(array_qubits[1])

    state_result("r", array_qubits[0], array_qubits[1])
    discard_array(array_qubits)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
