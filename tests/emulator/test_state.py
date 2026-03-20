"""Unit tests for guppylang.emulator.state module."""

from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np
import pytest
from guppylang.emulator.state import NotSingleStateError, PartialVector


def test_incompatible_init_params():
    """Test that PartialVector raises ValueError for incompatible parameters."""
    with pytest.raises(ValueError, match="Base state vector length"):
        PartialVector(base_state=np.array([1, 0]), total_qubits=3, specified_qubits=[0])


def test_not_single_state_error_str_representation():
    """Test string representation of the error."""
    error = NotSingleStateError(total_qubits=5, n_specified_qubits=3)
    expected = (
        "Selene state is not a single state: total qubits 5 != specified qubits 3."
    )
    assert str(error) == expected


@patch("guppylang.emulator.state.SeleneQuestState")
def test_partial_vector_init(mock_selene_quest_state):
    """Test PartialVector initialization."""
    # Create mock SeleneQuestState for testing
    mock_selene_state = Mock()
    mock_selene_state.total_qubits = 3
    mock_selene_state.specified_qubits = [0, 1, 2]
    mock_selene_quest_state.return_value = mock_selene_state

    # Sample state vector for 3 qubits
    sample_state = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.complex128)

    state = sample_state
    total_qubits = 3
    specified_qubits = [0, 1, 2]

    pv = PartialVector(state, total_qubits, specified_qubits)

    mock_selene_quest_state.assert_called_once_with(
        state=state, total_qubits=total_qubits, specified_qubits=specified_qubits
    )
    assert pv._inner == mock_selene_state


def test_partial_vector_properties():
    """Test total_qubits property."""
    state = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.complex128)
    pv = PartialVector(state, total_qubits=3, specified_qubits=[0, 1, 2])

    assert str(pv) == "PartialVector(total_qubits=3, specified_qubits=[0, 1, 2])"
    assert pv.total_qubits == 3
    assert pv.specified_qubits == [0, 1, 2]


INV_ROOT_2 = 1 / np.sqrt(2)


def test_partial_vector_state_distribution():
    """Test state_distribution method."""
    state = np.array([INV_ROOT_2, 0, 0, INV_ROOT_2], dtype=np.complex128)
    pv = PartialVector(state, total_qubits=2, specified_qubits=[0])

    with pytest.raises(NotSingleStateError):
        pv.as_single_state()

    result = pv.state_distribution(zero_threshold=1e-10)

    assert len(result) == 2
    for state in result:
        assert np.isclose(state.probability, 0.5)
        assert len(state.state) == 2
    assert np.allclose(result[0].state, np.array([1, 0]))
    assert np.allclose(result[1].state, np.array([0, 1]))


def test_partial_vector_as_single_state():
    """Test as_single_state method."""
    state = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.complex128)
    pv = PartialVector(state, total_qubits=3, specified_qubits=[0, 1, 2])

    result = pv.as_single_state(zero_threshold=1e-10)

    assert np.allclose(result, state)
