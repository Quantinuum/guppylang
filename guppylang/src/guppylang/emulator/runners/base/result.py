"""Class for runner results."""

from dataclasses import dataclass

from hugr.qsystem.result import QsysResult
from pytket.circuit import Circuit
from selene_sim.event_hooks import (
    CircuitExtractor,
    MetricStore,
    MultiEventHook,
    NoEventHook,
)


@dataclass(frozen=True)
class RunResult:
    """Result of running a program on a backend."""

    results: QsysResult
    event_hook: MultiEventHook | NoEventHook | CircuitExtractor | MetricStore | None

    def get_circuits(self, n_qubits: int) -> list[Circuit]:
        """Get the circuits used in the simulation."""
        event_hook = self.event_hook
        if event_hook is None or isinstance(event_hook, NoEventHook):
            raise ValueError(
                "No event hook found in the run result. "
                "Cannot extract circuits without an event hook."
            )
        elif isinstance(event_hook, MultiEventHook):
            for hook in event_hook.event_hooks:
                if isinstance(hook, CircuitExtractor):
                    event_hook = hook
                    break
        assert isinstance(event_hook, CircuitExtractor), (
            "Event hook is not a CircuitExtractor. Cannot extract circuits."
        )
        circuits = []
        for shot_instructions in event_hook.shots:
            circuit = Circuit(n_qubits)
            for instruction in shot_instructions:
                instruction.operation.append_to_circuit(circuit)
            circuits.append(circuit)
        return circuits
