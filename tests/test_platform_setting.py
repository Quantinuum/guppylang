"""Tests for the target platform configuration in `.emulator`."""

from __future__ import annotations

from unittest.mock import Mock, patch

from guppylang import guppy


@patch("guppylang.emulator.builder.selene_sim.build", return_value=Mock())
def test_target_platform_used_by_emulator(mock_build: Mock) -> None:
    """Test that the configured target platform is forwarded to the emulator."""

    @guppy
    def main() -> None:
        pass

    main.with_target_platform("sol").emulator(n_qubits=0)

    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs["platform"] == "sol"


@patch("guppylang.emulator.builder.selene_sim.build", return_value=Mock())
def test_emulator_platform_argument_overrides_target(mock_build: Mock) -> None:
    """Test that an explicit emulator platform overrides the configured target."""

    @guppy
    def main() -> None:
        pass

    main.with_target_platform("sol").emulator(n_qubits=0, platform="helios")

    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs["platform"] == "helios"
