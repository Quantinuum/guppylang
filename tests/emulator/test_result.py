"""Unit tests for guppylang.emulator.result module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from guppylang.emulator.result import EmulatorResult
from hugr.qsystem.result import QsysShot

if TYPE_CHECKING:
    from guppylang.emulator import MetricGroup, MetricValue, ShotMetrics


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


def test_emulator_result_analysis_requires_collection():
    """Analysis accessors explain how to enable their collection."""
    result = EmulatorResult()

    with pytest.raises(RuntimeError, match=r"with_trace\(\)"):
        result.traces()
    with pytest.raises(RuntimeError, match=r"with_trace\(\)"):
        result.circuits()
    with pytest.raises(RuntimeError, match=r"with_metrics\(\)"):
        result.metrics()


def test_emulator_result_analysis_accessors():
    """Analysis accessors return the data recorded by their collectors."""
    trace, circuit = Mock(), Mock()
    shot = Mock()
    shot.get_trace.return_value = trace
    shot.get_user_circuit.return_value = circuit
    circuit_extractor = Mock(shots=[shot])
    metric_store = Mock(shots=[{"user_program": {"measure_count": 1}}])
    result = EmulatorResult(
        [QsysShot()],
        _circuit_extractor=circuit_extractor,
        _metric_store=metric_store,
    )

    assert result.traces() == [trace]

    with patch("guppylang.emulator.result.import_module"):
        assert result.circuits() == [circuit]

    assert result.metrics() == [{"user_program": {"measure_count": 1}}]
    metric_value: MetricValue = 1
    metric_group: MetricGroup = {"measure_count": metric_value}
    shot_metrics: ShotMetrics = {"user_program": metric_group}
    assert shot_metrics == {"user_program": {"measure_count": 1}}
