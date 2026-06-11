"""Test the use of a classical function inside modifiers"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, angle, measure
from guppylang.std.quantum import h, rx, x

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def fuu(i: int) -> int:
    q = qubit()
    x(q)
    if measure(q):
        i = i + 1
    return i


@guppy
def main() -> None:
    t = qubit()
    c1 = qubit()
    h(c1)
    with control(c1):
        d = fuu(2)
        with dagger:
            rx(t, angle(1 / d))

    state_result("r", c1, t)
    discard(c1)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
