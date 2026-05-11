from enum import Enum


class Effect(Enum):
    names = ()

    @classmethod
    def __from_str__(cls, s: str) -> "Effect":
        for effect in cls:
            if effect.name == s:
                return effect
        raise ValueError(f"Invalid effect name: {s}")
