"""Configuration for running on Nexus backends."""

import uuid

import pydantic as pyd
from quantinuum_schemas.models.backend_config import (
    HeliosConfig,
    HeliosEmulatorConfig,
    SeleneConfig,
    SelenePlusConfig,
)
from quantinuum_schemas.models.emulator_config import StatevectorSimulator

from guppylang.defs import GuppyFunctionDefinition
from guppylang.emulator.runners.base.backend_config import RunnerConfig


class NexusRunnerConfig(RunnerConfig):
    """Config for running on Nexus backends.

    NOTE that this is a very basic support for Nexus backends and to be improved
    in the future according to user needs and feedback.
    """

    project_name: str

    backend_config: HeliosConfig | SeleneConfig | SelenePlusConfig

    job_name_suffix: uuid.UUID | str = pyd.Field(default_factory=uuid.uuid1)

    def model_post_init(self, context):
        """Post-initialization to validation."""
        super().model_post_init(context)
        emulator_config = getattr(
            self.backend_config, "emulator_config", self.backend_config
        )
        if (
            hasattr(emulator_config, "n_qubits")
            and emulator_config.n_qubits != self.n_qubits
        ):
            raise ValueError(
                "Number of qubits in the run config must match "
                "the number of qubits in the backend config"
            )

    @staticmethod
    def create_Helios_emulation_config(
        program: GuppyFunctionDefinition,
        n_qubits: int,
        n_shots: int,
        project_name: str,
        seed: int | None = None,
    ) -> "NexusRunnerConfig":
        """Create a NexusRunnerConfig for emulating Helios hardware on Nexus."""
        backend_config = NexusRunnerConfig.get_default_Helios_emulation_config(
            n_qubits=n_qubits
        )
        return NexusRunnerConfig(
            program=program,
            n_qubits=n_qubits,
            n_shots=n_shots,
            seed=seed,
            backend_config=backend_config,
            project_name=project_name,
        )

    @staticmethod
    def create_Helios_config(
        program: GuppyFunctionDefinition,
        n_qubits: int,
        n_shots: int,
        project_name: str,
        seed: int | None = None,
    ) -> "NexusRunnerConfig":
        """Create a NexusRunnerConfig for running on Helios hardware through Nexus."""
        backend_config = NexusRunnerConfig.get_default_Helios_config()
        return NexusRunnerConfig(
            program=program,
            n_qubits=n_qubits,
            n_shots=n_shots,
            seed=seed,
            backend_config=backend_config,
            project_name=project_name,
        )

    @staticmethod
    def get_default_Helios_emulation_config(
        n_qubits: int, max_cost: int = 1000
    ) -> HeliosConfig:
        """Get a default HeliosConfig for emulating Helios hardware on Nexus."""
        return HeliosConfig(
            system_name="Helios-1E",
            max_cost=max_cost,
            emulator_config=HeliosEmulatorConfig(
                n_qubits=n_qubits, simulator=StatevectorSimulator()
            ),
        )

    @staticmethod
    def get_default_Helios_config(max_cost: float | None = None) -> HeliosConfig:
        """Get a default HeliosConfig for running on Helios hardware through Nexus."""
        return HeliosConfig(
            system_name="Helios-1",
            max_cost=max_cost,
        )
