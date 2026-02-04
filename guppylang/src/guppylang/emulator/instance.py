"""
Configuring and executing emulator instances for guppy programs.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, cast

from hugr.qsystem.result import QsysShot
from selene_sim.backends.bundled_error_models import IdealErrorModel
from selene_sim.backends.bundled_runtimes import SimpleRuntime
from selene_sim.backends.bundled_simulators import Coinflip, Quest, Stim
from selene_sim.event_hooks import EventHook, NoEventHook
from tqdm import tqdm
from typing_extensions import Self

from .exceptions import EmulatorError
from .result import EmulatorResult

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterator
    from pathlib import Path

    from hugr.qsystem.result import TaggedResult
    from selene_core.error_model import ErrorModel
    from selene_core.runtime import Runtime
    from selene_core.simulator import Simulator
    from selene_sim.instance import SeleneInstance


@dataclass(frozen=True)
class _Options:
    _simulator: Simulator = field(default_factory=Quest)
    _runtime: Runtime = field(default_factory=SimpleRuntime)
    _error_model: ErrorModel = field(default_factory=IdealErrorModel)
    _shots: int = 1
    _shot_increment: int = 1
    _shot_offset: int = 0
    _seed: int | None = None
    _verbose: bool = False
    _timeout: datetime.timedelta | None = None
    _n_processes: int = 1
    _event_hook: EventHook = field(default_factory=NoEventHook)
    # unstable:
    _results_logfile: Path | None = None
    _display_progress_bar: bool = False


@dataclass(frozen=True)
class EmulatorInstance:
    """An emulator instance for running a compiled program.


    Returned by :py:class:`GuppyFunctionDefinition.emulator`.
    Contains configuration options for the emulator instance, such as the number of
    qubits, the number of shots, the simulator backend, and more.
    """

    _instance: SeleneInstance
    _n_qubits: int
    _options: _Options = field(default_factory=_Options)

    def _with_option(self, **kwargs: Any) -> Self:
        """Helper method to simplify setting options."""
        return replace(self, _options=replace(self._options, **kwargs))

    @property
    def n_qubits(self) -> int:
        """Number of qubits available in the emulator instance."""
        return self._n_qubits

    @property
    def shots(self) -> int:
        """Number of shots to run for each execution."""
        return self._options._shots

    @property
    def simulator(self) -> Simulator:
        """Simulation backend used for running the emulator instance."""
        return self._options._simulator

    @property
    def runtime(self) -> Runtime:
        """Runtime used for executing the emulator instance."""
        return self._options._runtime

    @property
    def error_model(self) -> ErrorModel:
        """Device error model used for the emulator instance."""
        return self._options._error_model

    @property
    def verbose(self) -> bool:
        """Whether to print verbose output during the emulator execution."""
        return self._options._verbose

    @property
    def timeout(self) -> datetime.timedelta | None:
        """Timeout for the emulator execution, if any."""
        return self._options._timeout

    @property
    def seed(self) -> int | None:
        """Random seed for the emulator instance, if any."""
        return self._options._seed

    @property
    def shot_offset(self) -> int:
        """Offset for the shot numbers, shot counts will begin at this offset.
        Defaults to 0.

        This is useful for running multiple emulator instances in parallel"""
        return self._options._shot_offset

    @property
    def shot_increment(self) -> int:
        """Value to increment shot numbers by for each repeated run.
        Defaults to 1."""
        return self._options._shot_increment

    @property
    def n_processes(self) -> int:
        """Number of processes to parallelise the emulator execution across.
        Defaults to 1, meaning no parallelisation."""
        return self._options._n_processes

    def with_n_qubits(self, value: int) -> Self:
        """Set the number of qubits available in the emulator instance."""
        return replace(self, _n_qubits=value)

    def with_shots(self, value: int) -> Self:
        """Set the number of shots to run for each execution.
        Defaults to 1."""
        return self._with_option(_shots=value)

    def with_simulator(self, value: Simulator) -> Self:
        """Set the simulation backend used for running the emulator instance.
        Defaults to statevector simulation."""
        return self._with_option(_simulator=value)

    def with_runtime(self, value: Runtime) -> Self:
        """Set the runtime used for executing the emulator instance.
        Defaults to SimpleRuntime."""
        return self._with_option(_runtime=value)

    def with_error_model(self, value: ErrorModel) -> Self:
        """Set the device error model used for the emulator instance.
        Defaults to IdealErrorModel (no errors)."""
        return self._with_option(_error_model=value)

    def with_event_hook(self, value: EventHook) -> Self:
        """Set the event hook used for the emulator instance.
        Defaults to NoEventHook."""
        return self._with_option(_event_hook=value)

    def with_verbose(self, value: bool) -> Self:
        """Set whether to print verbose output during the emulator execution.
        Defaults to False."""
        return self._with_option(_verbose=value)

    def with_progress_bar(self, value: bool = True) -> Self:
        """Set whether to display a progress bar during the emulator execution.
        Defaults to False."""
        return self._with_option(_display_progress_bar=value)

    def with_timeout(self, value: datetime.timedelta | None) -> Self:
        """Set the timeout for the emulator execution.
        Defaults to None (no timeout)."""
        return self._with_option(_timeout=value)

    def with_seed(self, value: int | None) -> Self:
        """Set the random seed for the emulator instance.
        Defaults to None."""
        new_options = replace(self._options, _seed=value)
        # TODO flaky stateful, remove when selene simplifies
        new_options._simulator.random_seed = value
        out = replace(self, _options=new_options)
        return out

    def with_shot_offset(self, value: int) -> Self:
        """Set the offset for the shot numbers, shot counts will begin at this offset.
        Defaults to 0.

        This is useful for running multiple emulator instances in parallel."""
        return self._with_option(_shot_offset=value)

    def with_shot_increment(self, value: int) -> Self:
        """Set the value to increment shot numbers by for each repeated run.
        Defaults to 1."""
        return self._with_option(_shot_increment=value)

    def with_n_processes(self, value: int) -> Self:
        """Set the number of processes to parallelise the emulator execution across.
        Defaults to 1, meaning no parallelisation."""
        return self._with_option(_n_processes=value)

    def statevector_sim(self) -> Self:
        """Set the simulation backend to the default statevector simulator."""
        return self.with_simulator(Quest())

    def coinflip_sim(self) -> Self:
        """Set the simulation backend to the coinflip simulator.
        This performs no quantum simulation, and flips a coin for each measurement."""
        return self.with_simulator(Coinflip())

    def stabilizer_sim(self) -> Self:
        """Set the simulation backend to the stabilizer simulator.
        This only works for clifford circuits but is very fast."""
        return self.with_simulator(Stim())

    def run(self) -> EmulatorResult:
        """Run the emulator instance and return the results.
        By default runs one shot, this can be configured with `with_shots()`."""
        result_stream = self._run_instance()

        all_results: list[QsysShot] = []
        for shot in self._iterate_shots(result_stream):
            shot_results = QsysShot()
            try:
                for tag, value in shot:
                    shot_results.append(tag, value)
            except Exception as e:  # noqa: BLE001
                # In this case, casting a wide net on exceptions is
                # suitable.
                raise EmulatorError(
                    completed_shots=EmulatorResult(all_results),
                    failing_shot=shot_results,
                    underlying_exception=e,
                ) from None
            all_results.append(shot_results)
        return EmulatorResult(all_results)

    def _run_instance(self) -> Iterator[Iterator[TaggedResult]]:
        """Run the Selene instance with the given simulator lazily."""
        return self._instance.run_shots(
            simulator=self.simulator,
            runtime=self.runtime,
            n_qubits=self.n_qubits,
            n_shots=self.shots,
            event_hook=self._options._event_hook,
            error_model=self.error_model,
            verbose=self.verbose,
            timeout=self.timeout,
            results_logfile=self._options._results_logfile,
            random_seed=self.seed,
            shot_offset=self.shot_offset,
            shot_increment=self.shot_increment,
            n_processes=self.n_processes,
        )

    def _iterate_shots(
        self, result_stream: Iterator[Iterator[TaggedResult]]
    ) -> Iterator[Iterator[TaggedResult]]:
        """Iterate over the shots in the result stream, optionally displaying a progress
        bar."""
        if self._options._display_progress_bar:
            return cast(
                "Iterator[Iterator[TaggedResult]]",
                tqdm(result_stream, total=self.shots, desc="Emulating shots"),
            )
        else:
            return result_stream
