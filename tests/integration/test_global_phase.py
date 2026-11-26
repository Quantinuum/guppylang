import numpy as np
from pytket.circuit import CircBox, Circuit, DiagonalBox, QControlBox

from guppylang import guppy
from guppylang.std.angles import pi
from guppylang.std.array import array
from guppylang.std.builtins import control, owned
from guppylang.std.lang import dagger
from guppylang.std.global_phase import global_phase
from guppylang.std.quantum import crz, discard, h, qubit, rz


# Test global phase can be used in allowed contexts.
def test_global_phase_quantum_input(validate) -> None:
    @guppy
    def foo(q: qubit @ owned) -> None:
        global_phase(pi)
        discard(q)

    validate(foo.compile_function())


def test_global_phase_quantum_output(validate) -> None:
    @guppy
    def foo() -> qubit:
        global_phase(pi)
        return qubit()

    validate(foo.compile_function())


def test_global_phase_in_dagger_block(validate) -> None:
    @guppy
    def foo(q: qubit) -> None:
        with dagger:
            global_phase(pi)

    validate(foo.compile_function())


def test_global_phase_comptime(validate) -> None:
    @guppy.comptime
    def foo(q: qubit) -> None:
        global_phase(pi)

    validate(foo.compile_function())


def test_global_phase_generic_instantiated_with_qubit(validate) -> None:
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy
    def phase(q: T) -> None:
        global_phase(pi)

    @guppy
    def main(q: qubit) -> None:
        phase(q)

    validate(main.compile_function())


# Test global phase results in the expected state when controlled. Expected states come
# from equivalent pytket circuits (pytket angles are in half-turns).
def test_controlled_global_phase(run_statevector_fn) -> None:
    @guppy
    def main() -> array[qubit, 2]:
        q = qubit()
        t = qubit()
        h(q)
        with control(q):
            global_phase(pi / 3)
        return array(q, t)

    block = Circuit(1)
    block.add_phase(1 / 3)
    circ = Circuit(2)
    circ.H(0)
    circ.add_qcontrolbox(QControlBox(CircBox(block), 1), [0, 1])

    run_statevector_fn(main, expected=circ.get_statevector(), num_qubits=2)


def test_controlled_diagonal_unitary(run_statevector_fn) -> None:
    @guppy(controllable=True)
    def d(a: qubit, b: qubit) -> None:
        global_phase(3 * pi / 32)
        rz(a, 3 * pi / 16)
        crz(a, b, -pi / 8)

    @guppy
    def main() -> array[qubit, 3]:
        c = qubit()
        a = qubit()
        b = qubit()
        h(c)
        h(a)
        h(b)
        with control(c):
            d(a, b)
        return array(c, a, b)

    diag = np.array([1, 1, np.exp(1j * np.pi / 4), np.exp(1j * np.pi / 8)])
    circ = Circuit(3)
    circ.H(0)
    circ.H(1)
    circ.H(2)
    circ.add_qcontrolbox(QControlBox(DiagonalBox(diag), 1), [0, 1, 2])

    run_statevector_fn(main, expected=circ.get_statevector(), num_qubits=3)


# Test that adding controls to global phase produces expected unitaries.
def test_controlled_global_phase_is_rz(run_statevector_fn) -> None:
    @guppy
    def main() -> array[qubit, 1]:
        c = qubit()
        h(c)
        with control(c):
            global_phase(pi / 3)
        return array(c)

    circ = Circuit(1)
    circ.H(0)
    circ.Rz(1 / 3, 0)

    run_statevector_fn(main, expected=circ.get_statevector(), num_qubits=1)


def test_controlled_daggered_global_phase(run_statevector_fn) -> None:
    @guppy(controllable=True)
    def foo(q: qubit) -> None:
        with dagger:
            global_phase(pi / 3)

    @guppy
    def main() -> array[qubit, 2]:
        c = qubit()
        t = qubit()
        h(c)
        with control(c):
            foo(t)
        return array(c, t)

    circ = Circuit(2)
    circ.H(0)
    circ.Rz(-1 / 3, 0)

    run_statevector_fn(main, expected=circ.get_statevector(), num_qubits=2)


def test_doubly_controlled_global_phase_is_cphase(run_statevector_fn) -> None:
    @guppy
    def main() -> array[qubit, 2]:
        a = qubit()
        b = qubit()
        h(a)
        h(b)
        with control(a, b):
            global_phase(pi / 3)
        return array(a, b)

    # cphase(a, b, theta) = rz(a, theta / 2); crz(a, b, theta)
    circ = Circuit(2)
    circ.H(0)
    circ.H(1)
    circ.Rz(1 / 6, 0)
    circ.CRz(1 / 3, 0, 1)

    run_statevector_fn(main, expected=circ.get_statevector(), num_qubits=2)
