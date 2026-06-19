"""
Configuring and executing emulator instances for guppy programs.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, cast

from hugr.qsystem.result import QsysShot
from selene_argreader_plugin import ArgProvider
from selene_sim.backends.bundled_error_models import IdealErrorModel
from selene_sim.backends.bundled_runtimes import SimpleRuntime
from selene_sim.backends.bundled_simulators import Coinflip, Quest, Stim
from selene_sim.event_hooks import EventHook, NoEventHook
from tqdm import tqdm
from typing_extensions import Self

from ._args import (
    ArgValue,
    EntrypointArgValueError,
    _validate_per_shot_args,
    _validate_record,
)
from .exceptions import EmulatorError
from .result import EmulatorResult

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterator, Mapping
    from pathlib import Path

    from hugr.qsystem.result import TaggedResult
    from selene_core.error_model import ErrorModel
    from selene_core.runtime import Runtime
    from selene_core.simulator import Simulator
    from selene_sim.instance import SeleneInstance

    from ._args import EntrypointArgSpec


def _to_provider_args(args: Mapping[str, ArgValue]) -> dict[str, ArgValue]:
    """Convert a mapping of argument values to a dict suitable for ``ArgProvider``.

    ``ArgProvider`` requires array arguments to be plain ``list``; this converts
    any other sequence (tuple, numpy array, etc.) to ``list``.
    """

    def _coerce(v: ArgValue) -> ArgValue:
        if isinstance(v, (bool, int, float)):
            return v
        if isinstance(v, Sequence):
            return list(v)
        raise TypeError(f"Unexpected argument value type: {type(v).__name__!r}")

    return {k: _coerce(v) for k, v in args.items()}


@dataclass(frozen=True)
class _Options:
    _simulator: Simulator = field(default_factory=Quest)
    _runtime: Runtime = field(default_factory=SimpleRuntime)
    _error_model: ErrorModel = field(default_factory=IdealErrorModel)
    _shots: int | None = None
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
    _arg_specs: tuple[EntrypointArgSpec, ...] = ()

    def _with_option(self, **kwargs: Any) -> Self:
        """Helper method to simplify setting options."""
        return replace(self, _options=replace(self._options, **kwargs))

    @property
    def n_qubits(self) -> int:
        """Number of qubits available in the emulator instance."""
        return self._n_qubits

    @property
    def shots(self) -> int:
        """Number of shots to run for each execution.

        Defaults to 1 when unset (``with_shots`` was never called).
        """
        return self._options._shots if self._options._shots is not None else 1

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

    def run(self, **args: ArgValue) -> EmulatorResult:
        """Run the emulator instance and return the results.

        By default runs one shot, this can be configured with `with_shots()`.

        If the entrypoint takes runtime arguments, their values must be passed as
        keyword arguments. Only ``bool``, signed ``int``, ``float``, and arrays of
        those types are supported. The same values are used for every shot. For
        example::

            main.emulator(n_qubits=2).run(theta=1.5, n=3)

        To vary arguments per shot, use :meth:`run_per_shot` instead.
        """
        if not self._arg_specs:
            if args:
                raise EntrypointArgValueError(
                    "This entrypoint takes no runtime arguments, but got: "
                    + ", ".join(f"`{name}`" for name in args)
                )
            return self._collect_results(self._run_instance())

        _validate_record(self._arg_specs, args)
        provider = ArgProvider()
        provider.set_constant_args(**_to_provider_args(args))
        with provider:
            return self._collect_results(self._run_instance())

    def run_per_shot(self, args: Sequence[Mapping[str, ArgValue]]) -> EmulatorResult:
        """Run the emulator with a different set of runtime arguments per shot.

        ``args`` is a sequence with one mapping of argument values per shot, so
        the number of shots run is ``len(args)``. For example::

            main.emulator(n_qubits=2).run_per_shot(
                [{"theta": 1.0, "n": 10}, {"theta": 2.5, "n": 20}]
            )

        Because each record corresponds to exactly one shot, the shot count is
        fixed by ``args``. If ``with_shots`` has been set explicitly to a value
        that disagrees with ``len(args)`` this raises, rather than silently
        picking one; not calling ``with_shots`` at all is always fine.

        For constant arguments shared across all shots, use :meth:`run` instead.
        """
        if not self._arg_specs:
            raise EntrypointArgValueError(
                "This entrypoint takes no runtime arguments; `run_per_shot` is not "
                "applicable."
            )
        _validate_per_shot_args(self._arg_specs, args)
        if self.shot_offset != 0:
            raise EntrypointArgValueError(
                "`run_per_shot` is not compatible with a non-zero shot offset "
                f"(got {self.shot_offset}); per-shot arguments are indexed from 0."
            )
        set_shots = self._options._shots
        if set_shots is not None and set_shots != len(args):
            raise EntrypointArgValueError(
                f"`with_shots` was set to {set_shots}, but `run_per_shot` was given "
                f"{len(args)} argument record(s); the shot count is fixed by the "
                "number of records. Remove the conflicting `with_shots` call."
            )

        instance = self.with_shots(len(args))
        provider = ArgProvider()
        provider.set_variable_args([_to_provider_args(record) for record in args])
        with provider:
            return instance._collect_results(instance._run_instance())

    def _collect_results(
        self, result_stream: Iterator[Iterator[TaggedResult]]
    ) -> EmulatorResult:
        """Drain a shot result stream into an :class:`EmulatorResult`."""
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
