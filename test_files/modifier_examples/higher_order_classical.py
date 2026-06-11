"""Test the use of a higher-order classical function inside modifiers"""

from pathlib import Path
from sys import argv
from typing import Callable

from guppylang import guppy
from guppylang.std.builtins import (
    Unitary,
    control,
    dagger,
)
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, angle, ry, rz, rx
from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(unitary=True)
def apply_c(
    g: Unitary[[qubit, angle], None],
    fun: Callable[[float], angle],
    q: qubit,
) -> None:
    a = fun(0.5)
    g(q, a)


@guppy
def fun(f: float) -> angle:
    return angle(f)


@guppy
def gun(f: float) -> angle:
    return angle(-f)


@guppy
def main() -> None:
    q = qubit()
    c = qubit()

    with dagger:
        apply_c(ry, gun, c)

    with control(c), dagger():
        apply_c(rz, fun, q)
        apply_c(rx, fun, q)

    state_result("r", c, q)
    discard(q)
    discard(c)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
