from guppylang.std.lang import dagger
import numpy as np

from guppylang import guppy

from guppylang.std.angles import angle, pi
from guppylang.std.builtins import control, owned
from guppylang.std.debug import state_output
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


# Test global phase results in the expected state when controlled.
def test_controlled_global_phase() -> None:
    @guppy
    def main() -> None:
        q = qubit()
        t = qubit()
        h(q)
        with control(q):
            global_phase(pi / 3)
        state_output("s", q, t)
        discard(q)
        discard(t)

    res = main.emulator(2).statevector_sim().with_shots(1).with_seed(12).run()
    state = res.partial_state_dicts()[0]["s"].as_single_state()

    from pytket.circuit import CircBox, Circuit, QControlBox

    block = Circuit(1)
    block.add_phase(1 / 3)
    circ = Circuit(2)
    circ.H(0)
    circ.add_qcontrolbox(QControlBox(CircBox(block), 1), [0, 1])
    expected = circ.get_statevector()
    np.testing.assert_allclose(state, expected, atol=1e-6)


def test_controlled_diagonal_unitary() -> None:
    @guppy(controllable=True)
    def d(a: qubit, b: qubit) -> None:
        global_phase(3 * pi / 32)
        rz(a, 3 * pi / 16)
        crz(a, b, -pi / 8)

    @guppy
    def main() -> None:
        c = qubit()
        a = qubit()
        b = qubit()
        h(c)
        h(a)
        h(b)
        with control(c):
            d(a, b)
        state_output("s", c, a, b)
        discard(c)
        discard(a)
        discard(b)

    res = main.emulator(3).statevector_sim().with_shots(1).with_seed(12).run()
    state = res.partial_state_dicts()[0]["s"].as_single_state()

    from pytket.circuit import Circuit, DiagonalBox, QControlBox

    diag = np.array([1, 1, np.exp(1j * np.pi / 4), np.exp(1j * np.pi / 8)])
    circ = Circuit(3)
    circ.H(0)
    circ.H(1)
    circ.H(2)
    circ.add_qcontrolbox(QControlBox(DiagonalBox(diag), 1), [0, 1, 2])
    expected = circ.get_statevector()
    np.testing.assert_allclose(state, expected, atol=1e-6)


# Test that adding controls to global phase produces expected unitaries.
def run_ignoring_phase(main, n_qubits: int) -> np.ndarray:
    res = main.emulator(n_qubits).statevector_sim().with_shots(1).with_seed(12).run()
    state = res.partial_state_dicts()[0]["s"].as_single_state()
    # Divide by the first entry to ignore any global phase difference.
    return state / state[0]


def test_controlled_global_phase_is_rz() -> None:
    @guppy
    def with_phase() -> None:
        c = qubit()
        h(c)
        with control(c):
            global_phase(pi / 3)
        state_output("s", c)
        discard(c)

    @guppy
    def with_rz() -> None:
        c = qubit()
        h(c)
        rz(c, pi / 3)
        state_output("s", c)
        discard(c)

    np.testing.assert_allclose(
        run_ignoring_phase(with_phase, 1), run_ignoring_phase(with_rz, 1), atol=1e-6
    )


def test_doubly_controlled_global_phase_is_cphase() -> None:
    @guppy
    def cphase(control: qubit, target: qubit, theta: angle) -> None:
        rz(control, theta / 2)
        crz(control, target, theta)

    @guppy
    def with_phase() -> None:
        a = qubit()
        b = qubit()
        h(a)
        h(b)
        with control(a, b):
            global_phase(pi / 3)
        state_output("s", a, b)
        discard(a)
        discard(b)

    @guppy
    def with_cphase() -> None:
        a = qubit()
        b = qubit()
        h(a)
        h(b)
        cphase(a, b, pi / 3)
        state_output("s", a, b)
        discard(a)
        discard(b)

    np.testing.assert_allclose(
        run_ignoring_phase(with_phase, 2), run_ignoring_phase(with_cphase, 2), atol=1e-6
    )
