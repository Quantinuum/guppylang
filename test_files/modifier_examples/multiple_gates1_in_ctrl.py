"""Testing a control modifier on multiple gates"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from guppylang.std.quantum import rz, h, angle

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    c = qubit()
    t = qubit()
    h(c)

    with control(c):
        h(t)
        rz(t, angle(1 / 3))
        h(t)

    state_result("r", c, t)
    discard(t)
    discard(c)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
