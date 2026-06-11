"""Testing a dagger modifier on multiple functions"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from guppylang.std.quantum import s, rx
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
def foo2(q: qubit) -> None:
    s(q)


@guppy(unitary=True)
def foo3(q: qubit, f: float) -> None:
    rx(q, angle(f))


@guppy
def main() -> None:
    t = qubit()

    with dagger:
        foo1(t)
        f = get_f()
        foo2(t)
        foo3(t, f)

    state_result("r", t)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
