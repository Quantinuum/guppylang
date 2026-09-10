import numpy as np
import pytest

from guppylang import guppy
from guppylang.std.angles import pi
from guppylang.std.builtins import control
from guppylang.std.debug import state_output
from guppylang.std.global_phase import global_phase
from guppylang.std.quantum import discard, h, qubit


@pytest.mark.skip("Global phase removed by DCE?")
def test_global_phase_baseline() -> None:
    @guppy
    def main() -> None:
        q = qubit()
        global_phase(pi / 3)
        state_output("s", q)
        discard(q)

    res = (
        main.with_minimal_opt()
        .emulator(1)
        .statevector_sim()
        .with_shots(1)
        .with_seed(12)
        .run()
    )
    state = res.partial_state_dicts()[0]["s"].as_single_state()
    expected = np.array([np.exp(1j * np.pi / 3), 0])
    np.testing.assert_allclose(state, expected, atol=1e-6)


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

    res = (
        main.with_minimal_opt()
        .emulator(1)
        .statevector_sim()
        .with_shots(1)
        .with_seed(12)
        .run()
    )
    state = res.partial_state_dicts()[0]["s"].as_single_state()
    expected = np.array([1, np.exp(1j * np.pi / 3)]) / np.sqrt(2)
    np.testing.assert_allclose(state, expected, atol=1e-6)
