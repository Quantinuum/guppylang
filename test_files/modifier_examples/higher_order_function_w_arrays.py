"""Test the use of a higher-order function with arrays inside modifiers"""

from pathlib import Path
from sys import argv

from guppylang import array, guppy
from guppylang.std.builtins import (
    Unitary,
    control,
    dagger,
)
from guppylang.std.debug import state_result
from guppylang.std.quantum import cx, discard_array, qubit
from guppylang.std.quantum import h, s
from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(unitary=True)
def apply_2qubit_gate(f: Unitary[[qubit, qubit], None], q: array[qubit, 3]) -> None:
    f(q[1], q[2])


@guppy(dagger=True, control=True)
def apply_dagger(f: Unitary[[qubit], None], q: array[qubit, 3]) -> None:
    f(q[1])
    apply_2qubit_gate(cx, q)


@guppy
def main() -> None:
    q = array(qubit(), qubit(), qubit())
    h(q[0])

    with dagger, control(q[0]):
        apply_dagger(s, q)
        apply_dagger(h, q)

    state_result("r", q)
    discard_array(q)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
