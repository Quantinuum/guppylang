"""A simple controlled gate using modifiers"""

from pathlib import Path
from sys import argv
import sys

from guppylang import array, guppy
from guppylang.std.builtins import control
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, discard_array, qubit, angle
from guppylang.std.quantum import h, x, rx

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def f(array_controllers: array[qubit, 3], c: qubit) -> None:
    a = angle(1 / 3)
    with control(array_controllers[0], c):
        h(array_controllers[1])
        with control(array_controllers[1]):
            rx(array_controllers[2], a)


@guppy
def main() -> None:
    q = qubit()
    array_controllers: array[qubit, 3] = array(qubit(), qubit(), qubit())
    x(array_controllers[0])
    h(q)
    f(array_controllers, q)

    state_result(
        "r", q, array_controllers[0], array_controllers[1], array_controllers[2]
    )
    discard_array(array_controllers)
    discard(q)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
