from collections.abc import Iterable
from enum import Enum


class Effect(Enum):
    """Any effect (aka side-effect) that a function or op may have that
    is not explicitly captured by dataflow in local variables. For example,
    reading or writing to a global variable, or performing I/O - including early
    termination of the program. (An op is called "pure" if it has no such effects.)
    """

    """For now, we do not distinguish between different kinds of effects,
    and instead totally order all functions/operations that have an effect;
    so this just flags any function or operation that is not pure."""
    ANY = "Any"

    @classmethod
    def __from_str__(cls, s: str) -> "Effect":
        for effect in cls:
            if effect.name == s:
                return effect
        raise ValueError(f"Invalid effect name: {s}")

    @staticmethod
    def format_list(effects: Iterable["Effect"]) -> str:
        return f"[{', '.join(e.name for e in effects)}]"
