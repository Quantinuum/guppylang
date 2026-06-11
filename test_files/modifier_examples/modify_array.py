"""Test control modifiers on an array element"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, array, discard_array
from guppylang.std.quantum import h

sys.path.append(str(Path(__file__).resolve().parents[1]))


from guppylang.experimental import enable_experimental_features

enable_experimental_features()

hugr_pdf_directory = Path(__file__).resolve().parents[1] / "0_hugr_pdf"
hugr_pdf_directory.mkdir(exist_ok=True)


@guppy
def main() -> None:
    q = qubit()
    h(q)
    array_controllers: array[qubit, 2] = array(qubit(), qubit())

    with control(q):
        h(array_controllers[1])

    state_result("r", q, array_controllers[0], array_controllers[1])
    discard_array(array_controllers)
    discard(q)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
