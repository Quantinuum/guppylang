from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    ParsableDef,
)

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals
    from guppylang_internals.span import SourceMap

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class RawModifierDef(ParsableDef):
    """A raw modifier definition provided by the user.

    Modifiers are special classes used in `with` statements. This definition is used
    only to detect unexpected errors
    """

    python_func: PyFunc

    description: str = field(default="modifier", init=False)

    def parse(self, globals: "Globals", sources: "SourceMap") -> "ParsedModifierDef":
        """Parses the raw modifier definition into a parsed definition."""
        # For now, modifiers don't need any parsing logic
        return ParsedModifierDef(self.id, self.name, self.defined_at)


@dataclass(frozen=True)
class ParsedModifierDef(CheckableDef):
    """A parsed modifier definition.

    Modifiers are special classes used in `with` statements. This definition is used
    only to detect unexpected errors"""

    description: str = field(default="modifier", init=False)

    def check(self, globals: "Globals") -> "CheckedModifierDef":
        return CheckedModifierDef(self.id, self.name, self.defined_at)


@dataclass(frozen=True)
class CheckedModifierDef(CompiledDef):
    """A checked modifier definition.

    Modifiers are special classes used in `with` statements. This definition is used
    only to detect unexpected errors"""
