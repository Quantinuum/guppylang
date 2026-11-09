from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class BaseEffect(Enum):
    """The types of independent effect we understand. Each has its own
    structure of order edges independent of other `BaseEffect`s.
    """

    """Nodes that affect the number of qubits available for allocation.
    We use `StronglyOrdered` for those which allocate, so that if we run
    out of qubits, the allocation that fails is the one that would be expected
    from executing the code in sequential order; but `WeaklyOrdered` for nodes
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

    """Models the state of the system-wide/global RNG."""
    RNG = "RNG"


@dataclass(frozen=True)
class StronglyOrdered:
    """Indicates that a node should be totally ordered i.e. after any previous nodes
    with the same `BaseEffect` (strong or weak).

    AKA TotalOrder, Sequential, Write
    """

    base: BaseEffect


@dataclass(frozen=True)
class WeaklyOrdered:
    """Indicates that a node should be ordered after any previous node
    which was `StronglyOrdered` for the same `BaseEffect`, but
    in parallel with other `WeaklyOrdered` nodes of the same `BaseEffect`
    (since the last `StronglyOrdered`).

    AKA PartialOrder, Parallel, Read
    """

    base: BaseEffect


type EffectType = StronglyOrdered | WeaklyOrdered


class Effect(Enum):
    """Any effect (aka side-effect) that a function or op may have that
    is not explicitly captured by dataflow in local variables. For example,
    reading or writing to a global variable, or performing I/O - including early
    termination of the program. (An op is called "pure" if it has no such effects.)
    """

    value: EffectType | Iterable[EffectType]

    """Outputting a result, which we insist must be returned in program order for
    processing."""
    OUTPUT = StronglyOrdered(BaseEffect.OUTPUT)
    """Early termination of the program with a failure. We insist that the correct
    values would be `OUTPUT` in such a case, but do not guarantee the specific message
    if there are multiple panics without intervening results."""
    PANIC = WeaklyOrdered(BaseEffect.OUTPUT)
    """Qubit allocation. Totally ordered for predictability i.e. so that if allocation
    fails then it does so as if the program executed sequentially."""
    ALLOC = StronglyOrdered(BaseEffect.ALLOCATION)
    """Freeing qubits. Parallel frees cannot affect each other but (for predictability)
    must occur in program order wrt. any allocations."""
    FREE = WeaklyOrdered(BaseEffect.ALLOCATION)

    """System-wide/global random number generator."""
    RNG = StronglyOrdered(BaseEffect.RNG)

    """Unknown effects - i.e. we must conservatively any and all the above."""
    ANY = tuple(StronglyOrdered(e) for e in BaseEffect)

    @classmethod
    def __from_str__(cls, s: str) -> "Effect":
        for effect in cls:
            if effect.name == s:
                return effect
        raise ValueError(f"Invalid effect name: {s}")

    @staticmethod
    def format_list(effects: Iterable["Effect"]) -> str:
        return f"[{', '.join(e.name for e in effects)}]"


def extract_effect_types(
    effects: Iterable[Effect | EffectType],
) -> Iterable[EffectType]:
    for e in effects:
        if isinstance(e, Effect):
            etys = e.value if isinstance(e.value, Iterable) else [e.value]
        else:
            etys = [e]
        for et in etys:
            if isinstance(et, StronglyOrdered):
                # Strong allows weak effects too
                yield WeaklyOrdered(et.base)
            yield et
