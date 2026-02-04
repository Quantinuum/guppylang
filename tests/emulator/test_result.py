"""Unit tests for guppylang.emulator.result module."""

from __future__ import annotations

from unittest.mock import Mock, patch

from guppylang.emulator.result import EmulatorResult


@patch("guppylang.emulator.result.Quest")
def test_emulator_result_methods_comprehensive(mock_quest):
    """Test EmulatorResult partial_states and partial_state_dicts methods
    Using mocked states."""

    # Setup mock states for two shots
    mock_state1, mock_state2, mock_state3 = Mock(), Mock(), Mock()
    mock_quest.extract_states.side_effect = [
        [("q0", mock_state1), ("q0", mock_state2)],  # First shot: 2 states
        [("q0", mock_state3)],  # Second shot: 1 state, duplicate tag
    ]

    result = EmulatorResult([[], []])  # two empty shots

    # Verify cache starts as None
    assert result._partial_states is None

    with patch("guppylang.emulator.result.PartialVector") as mock_pv:
        mock_pv1, mock_pv2, mock_pv3 = Mock(), Mock(), Mock()
        mock_pv._from_inner.side_effect = [mock_pv1, mock_pv2, mock_pv3]

        states1 = result.partial_states()

        assert len(states1) == 2
        assert states1[0] == [("q0", mock_pv1), ("q0", mock_pv2)]
        assert states1[1] == [("q0", mock_pv3)]

        # Test caching: second call returns same object
        states2 = result.partial_states()
        assert states1 is states2

        # Test partial_state_dicts method (dictionary conversion & overwrite)
        state_dicts = result.partial_state_dicts()
        assert len(state_dicts) == 2
        assert state_dicts[0] == {"q0": mock_pv2}
        assert state_dicts[1] == {"q0": mock_pv3}

        # Verify Quest.extract_states called once per shot due to caching
        assert mock_quest.extract_states.call_count == 2
        # Verify PartialVector._from_inner called for each state
        assert mock_pv._from_inner.call_count == 3
