"""Testing a dagger modifier on multiple functions"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from guppylang.std.quantum import s, rx, h
from guppylang.std.angles import angle

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def get_f() -> float:
    return 1 / 3


@guppy(unitary=True)
def foo1(q: qubit) -> None:
    rx(q, angle(1 / 2))


@guppy(unitary=True)
def foo2(q: qubit, f: float) -> None:
    s(q)
    rx(q, angle(f))


@guppy
def main() -> None:
    t = qubit()
    c = qubit()
    h(c)

    with dagger:
        with control(c):
            foo1(t)
            f = get_f()
            foo2(t, f)

    state_result("r", c, t)
    discard(t)
    discard(c)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
