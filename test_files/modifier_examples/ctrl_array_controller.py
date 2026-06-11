"""A controlled gate where the controller is an array of qubits"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import array, control
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, discard_array, qubit
from guppylang.std.quantum import h, x

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(unitary=True)
def bar(q: qubit) -> None:
    x(q)


@guppy
def main() -> None:
    controllers: array[qubit, 3] = array(qubit(), qubit(), qubit())
    t = qubit()

    h(controllers[0])
    h(controllers[1])
    h(controllers[2])

    with control(controllers):
        bar(t)

    state_result("r", controllers[0], controllers[1], controllers[2], t)

    discard_array(controllers)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
