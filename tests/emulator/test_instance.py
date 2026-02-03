"""Unit tests for guppylang.emulator.instance module."""

from __future__ import annotations

import datetime
from unittest.mock import Mock, patch

from guppylang.emulator.instance import EmulatorInstance
from guppylang.emulator.result import EmulatorResult
from selene_depolarizing_error_model_plugin import DepolarizingPlugin
from selene_sim import IdealErrorModel, NoEventHook, Quest, SimpleRuntime, Stim
from selene_sim.backends.bundled_simulators import Coinflip
from selene_soft_rz_runtime_plugin import SoftRZRuntimePlugin


def test_emulator_instance_init():
    """Test EmulatorInstance initialization."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    assert instance._instance == mock_selene_instance
    assert instance._n_qubits == n_qubits
    assert instance.n_qubits == n_qubits


def test_emulator_instance_n_qubits_property():
    """Test n_qubits property."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    assert instance.n_qubits == n_qubits


def test_emulator_instance_with_n_qubits():
    """Test with_n_qubits method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_n_qubits(10)

    assert new_instance.n_qubits == 10
    assert new_instance._instance == mock_selene_instance
    assert instance.n_qubits == n_qubits  # Original unchanged


def test_emulator_instance_default_options():
    """Test that default options are set correctly."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    # Test default values
    assert instance.shots == 1
    assert instance.shot_increment == 1
    assert instance.shot_offset == 0
    assert instance.seed is None
    assert instance.verbose is False
    assert instance.timeout is None
    assert instance.n_processes == 1
    assert instance.simulator == Quest()
    assert instance.runtime == SimpleRuntime()
    assert instance.error_model == IdealErrorModel()


def test_emulator_instance_with_shots():
    """Test with_shots method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_shots(100)

    assert new_instance.shots == 100
    assert instance.shots == 1  # Original unchanged


def test_emulator_instance_with_simulator():
    """Test with_simulator method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)
    simulator = Coinflip()

    new_instance = instance.with_simulator(simulator)

    assert new_instance.simulator == simulator
    assert new_instance.simulator != instance.simulator


def test_emulator_instance_with_runtime():
    """Test with_runtime method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)
    runtime = SimpleRuntime()

    new_instance = instance.with_runtime(runtime)

    assert new_instance.runtime == runtime


def test_emulator_instance_with_error_model():
    """Test with_error_model method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)
    error_model = IdealErrorModel()

    new_instance = instance.with_error_model(error_model)

    assert new_instance.error_model == error_model


def test_emulator_instance_with_event_hook():
    """Test with_event_hook method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)
    event_hook = NoEventHook()

    new_instance = instance.with_event_hook(event_hook)

    assert new_instance._options._event_hook == event_hook


def test_emulator_instance_with_verbose():
    """Test with_verbose method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_verbose(True)

    assert new_instance.verbose is True
    assert instance.verbose is False  # Original unchanged


def test_emulator_instance_with_timeout():
    """Test with_timeout method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)
    timeout = datetime.timedelta(seconds=30)

    new_instance = instance.with_timeout(timeout)

    assert new_instance.timeout == timeout
    assert instance.timeout is None  # Original unchanged


def test_emulator_instance_with_timeout_none():
    """Test with_timeout method with None value."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_timeout(None)

    assert new_instance.timeout is None


def test_emulator_instance_with_seed():
    """Test with_seed method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_seed(42)

    assert new_instance.seed == 42
    assert instance.seed is None  # Original unchanged
    # Test that simulator's random_seed is also set
    assert new_instance._options._simulator.random_seed == 42


def test_emulator_instance_with_seed_none():
    """Test with_seed method with None value."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_seed(None)

    assert new_instance.seed is None
    assert new_instance._options._simulator.random_seed is None


def test_emulator_instance_with_shot_offset():
    """Test with_shot_offset method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_shot_offset(10)

    assert new_instance.shot_offset == 10
    assert instance.shot_offset == 0  # Original unchanged


def test_emulator_instance_with_shot_increment():
    """Test with_shot_increment method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_shot_increment(5)

    assert new_instance.shot_increment == 5
    assert instance.shot_increment == 1  # Original unchanged


def test_emulator_instance_with_n_processes():
    """Test with_n_processes method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.with_n_processes(4)

    assert new_instance.n_processes == 4
    assert instance.n_processes == 1  # Original unchanged


def test_emulator_instance_statevector_sim():
    """Test statevector_sim convenience method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.statevector_sim()

    assert isinstance(new_instance.simulator, Quest)


def test_emulator_instance_coinflip_sim():
    """Test coinflip_sim convenience method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.coinflip_sim()

    assert isinstance(new_instance.simulator, Coinflip)


def test_emulator_instance_stabilizer_sim():
    """Test stabilizer_sim convenience method."""

    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = instance.stabilizer_sim()

    assert isinstance(new_instance.simulator, Stim)


@patch("guppylang.emulator.EmulatorInstance._iterate_shots")
def test_emulator_instance_run(mock_iterate):
    """Test run method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    # Mock the selene instance's run_shots method to return a result stream
    mock_result_stream = Mock()
    mock_selene_instance.run_shots.return_value = mock_result_stream

    assert instance.run() == EmulatorResult()

    # Check that EmulatorResult was created with the result stream
    mock_iterate.assert_called_once_with(mock_result_stream)


def test_emulator_instance_run_instance():
    """Test _run_instance method."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    # Mock the selene instance's run_shots method
    mock_result_stream = Mock()
    mock_selene_instance.run_shots.return_value = mock_result_stream

    result_stream = instance._run_instance()

    # Check that run_shots was called with correct parameters
    mock_selene_instance.run_shots.assert_called_once_with(
        simulator=instance.simulator,
        runtime=instance.runtime,
        n_qubits=instance.n_qubits,
        n_shots=instance.shots,
        event_hook=instance._options._event_hook,
        error_model=instance.error_model,
        verbose=instance.verbose,
        timeout=instance.timeout,
        results_logfile=instance._options._results_logfile,
        random_seed=instance.seed,
        shot_offset=instance.shot_offset,
        shot_increment=instance.shot_increment,
        n_processes=instance.n_processes,
    )

    assert result_stream == mock_result_stream


def test_emulator_instance_chaining_methods():
    """Test that methods can be chained together."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    new_instance = (
        instance.with_shots(100)
        .with_seed(42)
        .with_verbose(True)
        .coinflip_sim()
        .with_n_processes(4)
    )

    assert new_instance.shots == 100
    assert new_instance.seed == 42
    assert new_instance.verbose is True
    assert new_instance.n_processes == 4

    assert isinstance(new_instance.simulator, Coinflip)

    # Original should be unchanged
    assert instance.shots == 1
    assert instance.seed is None
    assert instance.verbose is False
    assert instance.n_processes == 1


def test_emulator_instance_immutability():
    """Test that EmulatorInstance is immutable (returns new instances)."""
    mock_selene_instance = Mock()
    n_qubits = 5

    instance = EmulatorInstance(_instance=mock_selene_instance, _n_qubits=n_qubits)

    # Test various modification methods
    new_instance1 = instance.with_shots(100)
    new_instance2 = instance.with_seed(42)
    new_instance3 = instance.with_verbose(True)

    # All should be different objects
    assert new_instance1 is not instance
    assert new_instance2 is not instance
    assert new_instance3 is not instance
    assert new_instance1 is not new_instance2
    assert new_instance2 is not new_instance3

    # Original should be unchanged
    assert instance.shots == 1
    assert instance.seed is None
    assert instance.verbose is False


def test_emulator_instance_full_configuration_workflow():
    """Test a complete configuration workflow."""
    mock_selene_instance = Mock()

    # Create instance and configure it
    instance = (
        EmulatorInstance(_instance=mock_selene_instance, _n_qubits=3)
        .with_shots(1000)
        .with_runtime(SoftRZRuntimePlugin())
        .with_error_model(DepolarizingPlugin())
        .with_seed(12345)
        .statevector_sim()
        .with_verbose(True)
        .with_n_processes(2)
    )

    # Verify all settings
    assert instance.n_qubits == 3
    assert instance.shots == 1000
    assert instance.seed == 12345
    assert instance.verbose is True
    assert instance.n_processes == 2

    assert isinstance(instance.simulator, Quest)

    # Test that run would call with correct parameters
    mock_result_stream = Mock()
    mock_selene_instance.run_shots.return_value = mock_result_stream

    with patch("guppylang.emulator.EmulatorInstance._iterate_shots") as mock_result:
        instance.run()

        # Verify the call was made with all configured parameters
        mock_selene_instance.run_shots.assert_called_once()
        call_kwargs = mock_selene_instance.run_shots.call_args.kwargs

        assert call_kwargs["n_qubits"] == 3
        assert isinstance(call_kwargs["runtime"], SoftRZRuntimePlugin)
        assert isinstance(call_kwargs["error_model"], DepolarizingPlugin)
        assert call_kwargs["n_shots"] == 1000
        assert call_kwargs["random_seed"] == 12345
        assert call_kwargs["verbose"] is True
        assert call_kwargs["n_processes"] == 2
        assert isinstance(call_kwargs["simulator"], Quest)

        mock_result.assert_called_once_with(mock_result_stream)
