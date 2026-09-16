"""Data types describing modifiers applied to function calls."""

from dataclasses import dataclass
from enum import Enum

from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.ty import (
    CALL_CONTROLLED_METHOD,
    CALL_CTRL_DAGGERED_METHOD,
    CALL_DAGGERED_METHOD,
)


class CustomModifierKind(Enum):
    """Kinds of custom implementations supported by ``@guppy.unitary``."""

    DAGGERED = CALL_DAGGERED_METHOD
    CONTROLLED = CALL_CONTROLLED_METHOD
    CTRL_DAGGERED = CALL_CTRL_DAGGERED_METHOD

    @property
    def takes_controls(self) -> bool:
        """Whether the implementation has a control-count parameter."""
        return self in {
            CustomModifierKind.CONTROLLED,
            CustomModifierKind.CTRL_DAGGERED,
        }


@dataclass(frozen=True)
class ModifierContext:
    """Dagger and control modifiers active at a call site."""

    daggered: bool = False
    control_sizes: tuple[int | Const, ...] = ()

    def compose(self, inner: "ModifierContext") -> "ModifierContext":
        """Compose this modifier context with an inner context."""
        return ModifierContext(
            daggered=self.daggered ^ inner.daggered,
            control_sizes=(*self.control_sizes, *inner.control_sizes),
        )

    def concrete_control_count(self) -> int:
        """Return the total number of controls in a concrete context."""
        total = 0
        for size in self.control_sizes:
            match size:
                case int() as value:
                    total += value
                case ConstValue(value=int() as value):
                    total += value
                case _:
                    raise ValueError("Control count is not concrete")
        return total

    def kind_required(self) -> CustomModifierKind | None:
        """Return the custom implementation kind required by this context."""
        if self.daggered and self.control_sizes:
            return CustomModifierKind.CTRL_DAGGERED
        if self.daggered:
            return CustomModifierKind.DAGGERED
        if self.control_sizes:
            return CustomModifierKind.CONTROLLED
        return None


NO_CALL_MODIFIERS = ModifierContext()
