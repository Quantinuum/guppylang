"""Nested modifiers with multiple control qubits"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, angle
from guppylang.std.quantum import h, rz

sys.path.append(str(Path(__file__).resolve().parents[1]))


from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    t = qubit()
    c1 = qubit()
    c2 = qubit()
    c3 = qubit()
    h(c1)
    h(c2)
    h(c3)
    h(t)
    with control(c1, c2):
        with control(c3):
            with dagger:
                rz(t, angle(1 / 2))

    state_result("r", c1, c2, c3, t)
    discard(c1)
    discard(c2)
    discard(c3)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
