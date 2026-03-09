from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn

from guppylang_internals.definition.common import (
    CheckableDef,
    ParsableDef,
)
from guppylang_internals.error import InternalGuppyError

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals
    from guppylang_internals.span import SourceMap

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class RawModifierDef(ParsableDef):
    """A raw modifier definition provided by the user.

    Modifiers are special classes used in `with` statements to modify the behavior
    of quantum operations (e.g., dagger, control, etc.).
    TODO: NICOLA - update all the doc string
    """

    python_func: PyFunc

    description: str = field(default="modifier", init=False)

    def parse(self, globals: "Globals", sources: "SourceMap") -> "ParsedModifierDef":
        """Parses the raw modifier definition into a parsed definition."""
        # For now, modifiers don't need any parsing logic
        return ParsedModifierDef(self.id, self.name, self.defined_at)


@dataclass(frozen=True)
class ParsedModifierDef(CheckableDef):
    """A parsed modifier definition."""

    description: str = field(default="modifier", init=False)

    def check(self, globals: "Globals") -> NoReturn:
        """Modifiers don't need checking, this should not be called."""
        raise InternalGuppyError("ParsedModifierDef.check() should not be called")

    def parse(self, globals: "Globals", sources: "SourceMap") -> NoReturn:
        """Modifiers are already parsed, this should not be called."""
        raise InternalGuppyError("ParsedModifierDef.parse() should not be called")
