from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Literal, NamedTuple, cast


# Marking these as private because I don't expect usage outside guppylang-internals.
class _BaseEffect(Enum):
    ALLOCATION = "Allocation"
    OUTPUT = "Output"


@dataclass(frozen=True)
class _StronglyOrdered:
    base: _BaseEffect


@dataclass(frozen=True)
class _WeaklyOrdered:
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
