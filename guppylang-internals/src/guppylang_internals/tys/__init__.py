from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Literal, NamedTuple, cast


# Marking these as private because I don't expect usage outside guppylang-internals.
class _BaseEffect(Enum):
    """The types of independent effect we understand. Each has its own
    structure of order edges independent of other `_BaseEffect`s
    """

    """Nodes that affect the number of qubits available for allocation.
    We use `_StronglyOrdered` for those which allocate, so that if we run
    out of qubits, the allocation that fails is the one that would be expected
    from executing the code in sequential order; but `_WeaklyOrdered` for nodes
    which free qubits (make them available for allocation in the future) as the
    relative order of freeing does not affect the success/failure of allocation.
    """

    ALLOCATION = "Allocation"
    """Nodes that affect the output visible as the program terminates.
    That is: anything that produces results, or early exits the program, should be
    `StronglyOrdered` here.
    However, nodes that panic, may be `WeaklyOrdered`, as when there are multiple
    panics, we allow these to execute in any order - preserving only the presence
    or absence of a panic, and do not guarantee the specific message.
    """
    OUTPUT = "Output"


@dataclass(frozen=True)
class _StronglyOrdered:
    """Indicates that a node should be totally ordered i.e. after any previous nodes
    with the same `_BaseEffect` (strong or weak).

    AKA TotalOrder, Sequential, Write
    """

    base: _BaseEffect


@dataclass(frozen=True)
class _WeaklyOrdered:
    """Indicates that a node should be ordered after any previous node
    which was `_StronglyOrdered` for the same `_BaseEffect`, but
    in parallel with other `_WeaklyOrdered` nodes of the same `_BaseEffect`
    (since the last `_StronglyOrdered`).

    AKA PartialOrder, Parallel, Read
    """

    base: _BaseEffect


type EffectType = _StronglyOrdered | _WeaklyOrdered


class Effect(Enum):
    value: EffectType | Iterable[EffectType]

    OUTPUT = _StronglyOrdered(_BaseEffect.OUTPUT)
    PANIC = _WeaklyOrdered(_BaseEffect.OUTPUT)
    ALLOC = _StronglyOrdered(_BaseEffect.ALLOCATION)
    FREE = _WeaklyOrdered(_BaseEffect.ALLOCATION)
    ANY = cast("Iterable[EffectType]", [_StronglyOrdered(e) for e in _BaseEffect])

    def _values(self) -> Iterable[EffectType]:
        if isinstance(self.value, Iterable):
            return self.value
        return [self.value]

    @classmethod
    def __from_str__(cls, s: str) -> "Effect":
        for effect in cls:
            if effect.name == s:
                return effect
        raise ValueError(f"Invalid effect name: {s}")

    @staticmethod
    def format_list(effects: Iterable["Effect"]) -> str:
        return f"[{', '.join(e.name for e in effects)}]"
