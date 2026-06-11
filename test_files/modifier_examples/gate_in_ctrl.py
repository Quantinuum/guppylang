"""A simple controlled gate using modifiers"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard
from guppylang.std.quantum import h, x

sys.path.append(str(Path(__file__).resolve().parents[1]))
from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    q1 = qubit()
    q2 = qubit()
    h(q1)
    with control(q1):
        x(q2)

    state_result("r", q1, q2)
    discard(q1)
    discard(q2)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
