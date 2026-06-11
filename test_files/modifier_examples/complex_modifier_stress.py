"""A stress test for nested control and dagger modifiers."""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import array, control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import (
    angle,
    discard,
    discard_array,
    measure,
    qubit,
    h,
    rx,
    rz,
    x,
)

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def measured_offset(i: int) -> int:
    q = qubit()
    x(q)
    if measure(q):
        i = i + 1
    return i


@guppy(unitary=True)
def rotation(q: qubit) -> None:
    rx(q, angle(-1 / 7))


@guppy(unitary=True)
def flip(q: qubit) -> None:
    x(q)


@guppy(unitary=True)
def phase_ladder(q: qubit) -> None:
    with dagger:
        rotation(q)
    x(q)
    rz(q, angle(1 / 5))


@guppy
def main() -> None:
    array_controllers: array[qubit, 2] = array(qubit(), qubit())
    control_a = qubit()
    control_b = qubit()
    control_c = qubit()
    target_a = qubit()
    target_b = qubit()
    target_c = qubit()

    h(array_controllers[0])
    h(array_controllers[1])
    h(control_a)
    h(control_b)
    h(control_c)
    h(target_a)
    h(target_b)
    h(target_c)

    with control(control_a):
        with dagger:
            rotation(target_a)

    with control(control_a, control_b):
        with dagger:
            phase_ladder(target_a)

    with dagger:
        with control(control_b):
            rotation(target_b)

    with control(array_controllers):
        with dagger:
            rotation(target_b)

    with control(control_a):
        denominator = measured_offset(4)
        with control(control_b, control_c):
            with dagger:
                rz(target_c, angle(1 / denominator))

    with dagger:
        with dagger:
            with control(control_c):
                flip(target_c)

    with control(control_a, control_b, control_c):
        with dagger:
            rz(target_c, angle(1 / 6))

    with control(control_a, control_b, control_c):
        a = 3
        x(target_a)
        with dagger:
            rz(target_b, angle(1 / a))
            with control(array_controllers):
                rz(target_c, angle(1 / (a + 2)))

    state_result(
        "r",
        array_controllers[0],
        array_controllers[1],
        control_a,
        control_b,
        control_c,
        target_a,
        target_b,
        target_c,
    )

    discard_array(array_controllers)
    discard(control_a)
    discard(control_b)
    discard(control_c)
    discard(target_a)
    discard(target_b)
    discard(target_c)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
