"""LocalRunner for running programs locally using Selene and its extensions."""


from hugr.package import Package
from hugr.qsystem.result import QsysResult
from selene_sim import Quest
from selene_sim.backends import IdealErrorModel, SimpleRuntime
from selene_sim.build import build
from selene_sim.event_hooks import (
    CircuitExtractor,
    MetricStore,
    MultiEventHook,
    NoEventHook,
)
from selene_sim.instance import SeleneInstance

from guppylang.defs import GuppyFunctionDefinition
from guppylang.emulator.runners.base.result import RunResult
from guppylang.emulator.runners.base.runner_base import (
    BuilderBase,
    CompilerBase,
    RunnerBase,
)

from .config import LocalRunnerConfig


class LocalBuilder(BuilderBase[LocalRunnerConfig, SeleneInstance]):
    """Builder for building a Hugr package into a Selene instance."""

    @staticmethod
    def build(*, config: LocalRunnerConfig, package: Package) -> SeleneInstance:
        """Build a Selene instance for the given Hugr package."""
        if config.runtime_register_hook is not None:
            config.runtime_register_hook()
        return build(package, config.program_name, **config.build_kwargs)


class LocalRunner(RunnerBase[LocalRunnerConfig, SeleneInstance]):
    """Runner for running programs locally using Selene and its extensions."""

    def __init__(
        self,
        *,
        compiler: CompilerBase[LocalRunnerConfig] | None = None,
        builder: BuilderBase[LocalRunnerConfig, SeleneInstance] | None = None,
    ):
        """Initialize the runner with the given compiler and builder."""
        compiler = compiler if compiler else CompilerBase()
        builder = builder if builder else LocalBuilder()
        super().__init__(compiler=compiler, builder=builder)

    def run(
        self, *, config: LocalRunnerConfig, program: GuppyFunctionDefinition
    ) -> RunResult:
        """Run the given algorithm using the given Selene instance.

        Configures the Selene run using the provided configuration.
        Returns a RunResult containing shot results, event hooks, raw results, etc.
        """
        assert isinstance(config, LocalRunnerConfig), (
            "Config must be an instance of LocalRunnerConfig."
        )
        self._compile_and_build(config=config, program=program)
        assert self._build_artifact is not None, (
            "Build artifact must be available to run."
        )
        default_backend = Quest()
        # Prepare an event hook
        if config.with_circuit_extraction and config.with_metric_store:
            event_hook = MultiEventHook(
                [MetricStore(), CircuitExtractor()], short_circuit=False
            )
        elif config.with_circuit_extraction:
            event_hook = CircuitExtractor()
        elif config.with_metric_store:
            event_hook = MetricStore()
        else:
            event_hook = NoEventHook()

        # Run shots and return result
        results = QsysResult(
            self._build_artifact.run_shots(
                config.backend if config.backend else default_backend,
                n_qubits=config.n_qubits,
                n_shots=config.n_shots,
                error_model=(
                    config.error_model if config.error_model else IdealErrorModel()
                ),
                runtime=config.runtime if config.runtime else SimpleRuntime(),
                event_hook=event_hook,
                random_seed=config.seed,
            )
        )
        return RunResult(results=results, event_hook=event_hook)
