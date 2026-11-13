from guppylang.std.lang import dagger
import numpy as np

from guppylang import guppy
from guppylang.std.angles import pi
from guppylang.std.builtins import control, owned
from guppylang.std.debug import state_output
from guppylang.std.global_phase import global_phase
from guppylang.std.quantum import discard, h, qubit
import pytest


@pytest.mark.skip("Skipping due to TKET state order bug")
def test_controlled_global_phase() -> None:
    # A global phase is only observable once it is controlled.
    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        with control(q):
            global_phase(pi / 3)
        state_output("s", q)
        discard(q)

    # TODO: Compare with pytket.
    res = main.emulator(1).statevector_sim().with_shots(1).with_seed(12).run()
    state = res.partial_state_dicts()[0]["s"].as_single_state()
    expected = np.array([1, np.exp(1j * np.pi / 3)]) / np.sqrt(2)
    np.testing.assert_allclose(state, expected, atol=1e-6)


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


@pytest.mark.skip("Skipping due to TKET state order bug")
def test_global_phase_in_dagger_block(validate, use_experimental_features) -> None:
    @guppy
    def foo() -> None:
        with dagger:
            global_phase(pi)

    validate(foo.compile_function())


def test_global_phase_comptime(validate) -> None:
    @guppy.comptime
    def foo(q: qubit) -> None:
        global_phase(pi)

    validate(foo.compile_function())
