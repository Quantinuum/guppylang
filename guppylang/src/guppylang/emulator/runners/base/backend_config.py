"""Input configurations for different backends."""

from abc import ABC
from dataclasses import dataclass

from selene_core import ErrorModel, Runtime


@dataclass(frozen=True)
class RunnerConfig(ABC):
    """Basic configuration for running algorithms on different backends."""

    n_qubits: int
    """Number of qubits to run the program with. Must be at least 1."""

    n_shots: int
    """Number of shots to run the program for. Must be at least 1."""

    seed: int | None = None
    """Random seed for the simulator. If None, a random seed will be used."""

    error_model: ErrorModel | None = None
    """Error model to use during simulation.
    If None, noise-free simulation will be used.
    """

    runtime: Runtime | None = None
    """Runtime to use during simulation. If None, a default runtime will be used."""

    program_name: str = "guppy_program"
    """Name of the program being run."""
