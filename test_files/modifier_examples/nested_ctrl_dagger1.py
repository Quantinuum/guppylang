"""Nested control and dagger modifiers in various combinations"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, angle
from guppylang.std.quantum import h, rx, x

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(unitary=True)
def rotation(q: qubit) -> None:
    rx(q, angle(-1 / 3))


@guppy(unitary=True)
def flip(q: qubit) -> None:
    x(q)


@guppy
def main() -> None:
    c1 = qubit()
    c2 = qubit()
    t1 = qubit()
    t2 = qubit()

    h(c1)
    h(c2)

    with control(c1):
        with dagger:
            rotation(t2)

    with dagger:
        with control(c2):
            rotation(t1)

    state_result("r", c1, c2, t1, t2)
    discard(c1)
    discard(c2)
    discard(t1)
    discard(t2)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
