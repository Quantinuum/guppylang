"""
Emulation results and post-processing.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from hugr.qsystem.result import QsysResult, QsysShot, TaggedResult
from selene_core.trace import Trace
from selene_sim.backends.bundled_simulators import Quest

from .state import PartialVector

if TYPE_CHECKING:
    from collections import Counter

    from hugr.qsystem.result import DataValue
    from pytket.backends.backendresult import BackendResult
    from pytket.circuit import Circuit
    from selene_quest_plugin.state import SeleneQuestState
    from selene_sim.event_hooks.instruction_log import CircuitExtractor
    from selene_sim.event_hooks.metrics import MetricStore


#: A scalar metric value emitted by an emulator component.
type MetricValue = float | int | bool | str
#: Named scalar metrics emitted by one emulator component.
type MetricGroup = dict[str, MetricValue]
#: Component metrics collected for one emulated shot.
type ShotMetrics = dict[str, MetricGroup]

# Re-exports QsysResult, QsysShot, and TaggedResult - breaking changes to those upstream
# classes should be treated as breaking changes to this module.
__all__ = [
    "EmulatorResult",
    "MetricGroup",
    "MetricValue",
    "QsysShot",
    "ShotMetrics",
    "TaggedResult",
    "Trace",
]


class EmulatorResult(QsysResult):
    r"""A result from running an emulator instance.


    Collects data from ``output("tag", val)`` calls in the guppy program. Includes
    results for all shots.

    Includes conversions to traditional distributions over bitstrings if a tagging
    convention is used, including conversion to a pytket BackendResult.

    Under this convention, tags are assumed to be a name of a bit register unless they
    fit the regex pattern ``^([a-z][\w_]*)\[(\d+)\]$`` (like ``my_Reg[12]``) in which
    case they are assumed to refer to the nth element of a bit register.

    For results of the form ``output("<register>", value)``, ``value`` can be ``{0, 1}``
    , wherein the register is assumed to be length 1, or lists over those values,
    wherein the list is taken to be the value of the entire register.

    For results of the form ``output("<register>[n]", value)`` ``value`` can only be
    ``{0,1}``. The register is assumed to be at least `n+1` in size and unset elements
    are assumed to be ``0``.

    Subsequent writes to the same register/element in the same shot will overwrite.

    To convert to a ``BackendResult`` all registers must be present in all shots, and
    register sizes cannot change between shots.

    """

    # cache for extracted partial states, since extraction cleans up the files
    _partial_states: list[list[tuple[str, PartialVector]]] | None = None
    _circuit_extractor: CircuitExtractor | None
    _metric_store: MetricStore | None
    #: List of QsysShot objects, each representing a single shot's results.
    results: list[QsysShot]

    # Re-define parent methods for documentation purposes

    def __init__(
        self,
        results: list[QsysShot] | None = None,
        *,
        _circuit_extractor: CircuitExtractor | None = None,
        _metric_store: MetricStore | None = None,
    ):
        super().__init__(results=results)
        self._partial_states = None
        self._circuit_extractor = _circuit_extractor
        self._metric_store = _metric_store

    def register_counts(
        self, strict_names: bool = False, strict_lengths: bool = False
    ) -> dict[str, Counter[str]]:
        return super().register_counts(
            strict_names=strict_names, strict_lengths=strict_lengths
        )

    def register_bitstrings(
        self, strict_names: bool = False, strict_lengths: bool = False
    ) -> dict[str, list[str]]:
        return super().register_bitstrings(
            strict_names=strict_names, strict_lengths=strict_lengths
        )

    def to_pytket(self) -> BackendResult:
        return super().to_pytket()

    def collated_shots(self) -> list[dict[str, list[DataValue]]]:
        return super().collated_shots()

    def collated_counts(self) -> Counter[tuple[tuple[str, str], ...]]:
        return super().collated_counts()

    def collated_digitstring_counts(self) -> Counter[tuple[tuple[str, str], ...]]:
        return super().collated_digitstring_counts()

    def partial_state_dicts(self) -> list[dict[str, PartialVector]]:
        """Extract state results from shot results in to dictionaries.

        Looks for outputs from `state_output("tag", qs)` calls in the guppy program.

        Returns:
            A list of dictionaries, each dictionary containing the tag as the key and
            the `PartialVector` as the value. Each dictionary corresponds to a shot.
            Repeated tags in a shot will overwrite previous values.
        """
        return [dict(x) for x in self.partial_states()]

    def partial_states(self) -> list[list[tuple[str, PartialVector]]]:
        """Extract state results from shot results.


        Looks for outputs from `state_output("tag", qs)` calls in the guppy program.

        Returns:
            A list (over shots) of lists. The outer list is over shots, and the inner
            is over the state results in that shot.
            Each inner list contains tuples of (string tag, PartialVector).
        """
        if self._partial_states is None:

            def to_partial(
                x: tuple[str, SeleneQuestState],
            ) -> tuple[str, PartialVector]:
                return x[0], PartialVector._from_inner(x[1])

            self._partial_states = [
                list(map(to_partial, Quest.extract_states(shot)))
                for shot in self.results
            ]
        return self._partial_states

    def traces(self) -> list[Trace]:
        """Return the per-shot record of instructions emitted during emulation.

        Each :py:class:`Trace` is an ordered collection of events emitted by the
        user program, runtime, error model, and simulator. Use its
        ``get_user_program_trace()``, ``get_runtime_trace()``,
        ``get_error_model_trace()``, and ``get_simulator_trace()`` methods to
        inspect an individual execution stage.

        Enable trace collection with :meth:`EmulatorInstance.with_trace` before
        running the emulator.
        """
        if self._circuit_extractor is None:
            raise RuntimeError(
                "Trace collection was not enabled; call `with_trace()` before running "
                "the emulator."
            )
        # Retain every started shot. Selene currently leaves failed-shot analysis
        # empty (an upstream bug), but future partial analysis must remain visible.
        return [shot.get_trace() for shot in self._circuit_extractor.shots]

    def circuits(self) -> list[Circuit]:
        """Return `pytket Circuit objects
        <https://docs.quantinuum.com/tket/api-docs/circuit.html>`_ representing
        the stream of gates output by the user program at emulation time.

        Circuits are extracted from each shot's trace in the gateset produced by
        compilation, typically the primitive gateset of the hardware platform
        being emulated.

        Enable trace collection with :meth:`EmulatorInstance.with_trace` before
        running the emulator. ``pytket`` availability is checked before conversion.
        """
        if self._circuit_extractor is None:
            raise RuntimeError(
                "Trace collection was not enabled; call `with_trace()` before running "
                "the emulator."
            )
        try:
            import_module("pytket")
        except ModuleNotFoundError as e:
            if e.name == "pytket":
                raise ImportError(
                    "Circuit extraction requires pytket. Install pytket to use "
                    "`circuits()`."
                ) from None
            raise
        # Retain every started shot. Selene currently leaves failed-shot analysis
        # empty (an upstream bug), but future partial analysis must remain visible.
        return [shot.get_user_circuit() for shot in self._circuit_extractor.shots]

    def metrics(self) -> list[ShotMetrics]:
        """Return collected metrics for each emulated shot.

        Metrics include gate-count and allocation statistics for the user program
        and the operations emitted after runtime processing.

        Enable metric collection with :meth:`EmulatorInstance.with_metrics` before
        running the emulator.
        """
        if self._metric_store is None:
            raise RuntimeError(
                "Metric collection was not enabled; call `with_metrics()` before "
                "running the emulator."
            )
        # Retain every started shot. Selene currently leaves failed-shot analysis
        # empty (an upstream bug), but future partial analysis must remain visible.
        return self._metric_store.shots
