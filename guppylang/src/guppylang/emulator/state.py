"""
Debug querying the internal state of the emulator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

import numpy as np
import numpy.typing as npt
from selene_quest_plugin.state import SeleneQuestState, TracedState
from typing_extensions import Self

__all__ = [
    "NotSingleStateError",
    "PartialState",
    "PartialVector",
    "StateVector",
    "TracedState",
]

#: Type encoding a single state. e.g. StateVector for a state vector.
S = TypeVar("S")
#: Type encoding a state vector, type alias for numpy array of complex numbers.
StateVector = npt.NDArray[np.complexfloating]


@dataclass(frozen=True)
class NotSingleStateError(Exception):
    """Raised when a Selene state is not a single state, i.e. it has unspecified qubits
    that have been traced out."""

    total_qubits: int
    n_specified_qubits: int

    def __str__(self) -> str:
        return (
            f"Selene state is not a single state: "
            f"total qubits {self.total_qubits} != "
            f"specified qubits {self.n_specified_qubits}."
        )


class PartialState(Protocol[S]):
    """Protocol for an emulator state type.
    Different simulation backends may have different state representations."""

    @property
    def total_qubits(self) -> int:
        """Total number of qubits in the state."""
        ...

    @property
    def specified_qubits(self) -> list[int]:
        """List of specified qubits in the state."""
        ...

    def state_distribution(self, zero_threshold: float = 1e-12) -> list[TracedState[S]]:
        """Distribution of states after tracing out unspecified qubits.
        In general this results in a distribution of states, each with a probability.

        Args:
            zero_threshold: Threshold for considering a state amplitude to be zero.
                Defaults to 1e-12.
        Returns:
            List of traced states, each with a state vector and a probability."""
        ...

    def as_single_state(self, zero_threshold: float = 1e-12) -> S:
        """If the state is a single pure state return it.

        Args:
            zero_threshold: Threshold for considering a state amplitude to be zero.
                Defaults to 1e-12.
        Raises:
            NotSingleStateError: If the state is not a pure state.
        Returns:
            The state as a single state type.
        """
        all_states = self.state_distribution(zero_threshold)
        if len(all_states) != 1:
            raise NotSingleStateError(
                total_qubits=self.total_qubits,
                n_specified_qubits=len(self.specified_qubits),
            )
        return all_states[0].state


class PartialVector(PartialState[StateVector]):
    """Partial state vector for simulator backends with statevector representation.
    Partial in the sense that some qubits may be traced out, and the state is
    represented as a distribution of state vectors.
    """

    _inner: SeleneQuestState

    def __init__(
        self, base_state: StateVector, total_qubits: int, specified_qubits: list[int]
    ) -> None:
        """Initialize a PartialVector from a base state vector, total qubits, and
        specified qubits.

        Args:
            base_state: The state vector over all qubits in the system.
            total_qubits: Total number of qubits in the system
            specified_qubits: List of specified qubits in the state. Those not in this
            list are considered traced out.
        """
        if len(base_state) != (1 << total_qubits):
            raise ValueError(
                f"Base state vector length ({len(base_state)}) does not match "
                f"2 ** total_qubits ({1 << total_qubits})."
            )
        self._inner = SeleneQuestState(
            state=base_state,
            total_qubits=total_qubits,
            specified_qubits=specified_qubits,
        )

    @property
    def total_qubits(self) -> int:
        """Total number of qubits in the state."""
        return self._inner.total_qubits

    @property
    def specified_qubits(self) -> list[int]:
        """List of specified qubits in the state. Those not in this
        list are considered traced out."""
        return self._inner.specified_qubits

    def state_distribution(
        self, zero_threshold: float = 1e-12
    ) -> list[TracedState[StateVector]]:
        out = self._inner.get_state_vector_distribution(zero_threshold=zero_threshold)

        # force float to remove numpy types
        return [TracedState(float(st.probability), st.state) for st in out]

    @classmethod
    def _from_inner(cls, inner: SeleneQuestState) -> Self:
        """Create a PartialVector from an inner SeleneQuestState."""
        obj = cls.__new__(cls)
        obj._inner = inner
        return obj

    def __str__(self) -> str:
        #  don't print base state as it may be large
        return (
            f"PartialVector(total_qubits={self.total_qubits}, "
            f"specified_qubits={self.specified_qubits})"
        )
