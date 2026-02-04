"""Unit tests for guppylang.emulator.builder module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from guppylang.emulator.builder import EmulatorBuilder


def test_emulator_builder_default_initialization():
    """Test EmulatorBuilder default initialization."""
    builder = EmulatorBuilder()

    assert builder.name is None
    assert builder.build_dir is None
    assert builder.verbose is False

    # Check internal attributes
    assert builder._name is None
    assert builder._build_dir is None
    assert builder._verbose is False
    assert builder._planner is None
    assert builder._utilities is None
    assert builder._interface is None
    assert builder._progress_bar is False
    assert builder._strict is False
    assert builder._save_planner is False
    assert builder._custom_args is None


@patch("guppylang.emulator.builder.selene_sim")
@patch("guppylang.emulator.builder.EmulatorInstance")
def test_emulator_builder_build(mock_emulator_instance, mock_selene_sim):
    """Test build method."""
    # Set up mocks
    mock_package = Mock()
    mock_selene_instance = Mock()
    mock_selene_sim.build.return_value = mock_selene_instance
    mock_emulator_result = Mock()
    mock_emulator_instance.return_value = mock_emulator_result

    builder = EmulatorBuilder()
    n_qubits = 5

    result = builder.build(mock_package, n_qubits)

    # Check that selene_sim.build was called with correct parameters
    mock_selene_sim.build.assert_called_once_with(
        mock_package,
        name=None,
        build_dir=None,
        interface=None,
        utilities=None,
        verbose=False,
        planner=None,
        progress_bar=False,
        strict=False,
        save_planner=False,
    )

    # Check that EmulatorInstance was created correctly
    mock_emulator_instance.assert_called_once_with(
        _instance=mock_selene_instance, _n_qubits=n_qubits
    )

    assert result == mock_emulator_result


@patch("guppylang.emulator.builder.selene_sim")
@patch("guppylang.emulator.builder.EmulatorInstance")
def test_emulator_builder_build_with_custom_parameters(
    mock_emulator_instance, mock_selene_sim
):
    """Test build method with custom parameters."""
    # Set up mocks
    mock_package = Mock()
    mock_selene_instance = Mock()
    mock_selene_sim.build.return_value = mock_selene_instance
    mock_emulator_result = Mock()
    mock_emulator_instance.return_value = mock_emulator_result

    # Create builder with custom parameters
    build_dir = Path("./custom_build")
    builder = (
        EmulatorBuilder()
        .with_name("custom_emulator")
        .with_build_dir(build_dir)
        .with_verbose(True)
        .with_build_arg("build_method", "via-llvm-ir")
    )

    n_qubits = 10

    result = builder.build(mock_package, n_qubits)

    # Check that selene_sim.build was called with custom parameters
    mock_selene_sim.build.assert_called_once_with(
        mock_package,
        name="custom_emulator",
        build_dir=build_dir,
        interface=None,
        utilities=None,
        verbose=True,
        planner=None,
        progress_bar=False,
        strict=False,
        save_planner=False,
        build_method="via-llvm-ir",
    )

    # Check that EmulatorInstance was created correctly
    mock_emulator_instance.assert_called_once_with(
        _instance=mock_selene_instance, _n_qubits=n_qubits
    )

    assert result == mock_emulator_result


def test_emulator_builder_chaining_methods():
    """Test that builder methods can be chained together."""
    build_dir = Path("./test_build")

    builder = (
        EmulatorBuilder()
        .with_name("chained_emulator")
        .with_build_dir(build_dir)
        .with_verbose(True)
    )

    assert builder.name == "chained_emulator"
    assert builder.build_dir == build_dir
    assert builder.verbose is True


def test_emulator_builder_immutability():
    """Test that EmulatorBuilder is immutable (returns new instances)."""
    builder = EmulatorBuilder()

    # Test various modification methods
    new_builder1 = builder.with_name("test1")
    new_builder2 = builder.with_build_dir(Path("./build"))
    new_builder3 = builder.with_verbose(True)
    new_builder4 = builder.with_build_arg("custom_arg", 42)

    # All should be different objects
    assert new_builder1 is not builder
    assert new_builder2 is not builder
    assert new_builder3 is not builder
    assert new_builder4 is not builder
    assert new_builder1 is not new_builder2
    assert new_builder2 is not new_builder3
    assert new_builder3 is not new_builder4

    # Original should be unchanged
    assert builder.name is None
    assert builder.build_dir is None
    assert builder.verbose is False
    assert builder.custom_args is None


def test_emulator_builder_reuse():
    """Test that the same builder can be used multiple times."""
    builder = EmulatorBuilder().with_name("reusable").with_verbose(True)

    with (
        patch("guppylang.emulator.builder.selene_sim") as mock_selene_sim,
        patch("guppylang.emulator.builder.EmulatorInstance") as mock_emulator_instance,
    ):
        mock_selene_sim.build.return_value = Mock()
        mock_emulator_instance.return_value = Mock()

        # Use builder multiple times
        mock_package1 = Mock()
        mock_package2 = Mock()

        builder.build(mock_package1, 5)
        builder.build(mock_package2, 3)

        # Should have been called twice
        assert mock_selene_sim.build.call_count == 2
        assert mock_emulator_instance.call_count == 2

        # Both calls should have used the same builder parameters
        calls = mock_selene_sim.build.call_args_list
        assert calls[0].kwargs["name"] == "reusable"
        assert calls[1].kwargs["name"] == "reusable"
        assert calls[0].kwargs["verbose"] is True
        assert calls[1].kwargs["verbose"] is True
