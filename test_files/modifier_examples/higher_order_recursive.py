"""Some simple nested higher order functions inside modifiers"""

from pathlib import Path
from sys import argv

from guppylang import guppy
from guppylang.std.builtins import (
    Unitary,
    control,
    dagger,
)
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from guppylang.std.quantum import h, s
from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(unitary=True)
def apply(f: Unitary[[qubit], None], q: qubit) -> None:
    apply1(f, q)


@guppy(unitary=True)
def apply1(f: Unitary[[qubit], None], q: qubit) -> None:
    apply2(f, q)


@guppy(unitary=True)
def apply2(f: Unitary[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def main() -> None:
    q = qubit()
    c = qubit()
    h(c)

    with control(c), dagger:
        apply(s, q)
        apply(h, q)

    state_result("r", c, q)
    discard(q)
    discard(c)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
