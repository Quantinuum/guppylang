"""Test the use of a higher-order function with loops inside modifiers"""

from pathlib import Path
from sys import argv

from guppylang import guppy
from guppylang.std.builtins import (
    Controllable,
    Unitary,
    array,
    control,
    dagger,
)
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard_array, qubit, angle, rz
from guppylang.std.quantum import h, rx
from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(unitary=True)
def apply_r(f: Unitary[[qubit, angle], None], q: array[qubit, 2], angle: angle) -> None:
    f(q[1], angle)


@guppy(controllable=True)
def apply_c(
    f: Controllable[[qubit], None], g: Unitary[[qubit, angle], None], q: qubit, b: bool
) -> None:
    n = 3
    if b:
        while n > 0:
            f(q)
            n -= 1
    else:
        for _ in range(2):
            g(q, angle(0.5))


@guppy
def main() -> None:
    qs: array[qubit, 2] = array(qubit(), qubit())
    h(qs[0])
    flag = 2 > 10
    with control(qs[0]):
        apply_c(h, rx, qs[1], True)
        apply_c(h, rx, qs[1], flag)

    with control(qs[0]), dagger:
        apply_r(rz, qs, angle(0.25))
        apply_r(rz, qs, angle(0.5))

    state_result("r", qs[0], qs[1])
    discard_array(qs)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
