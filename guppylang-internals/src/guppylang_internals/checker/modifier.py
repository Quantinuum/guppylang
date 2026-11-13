"""Data types describing modifiers applied to function calls."""

from dataclasses import dataclass
from enum import Enum

from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.ty import (
    CALL_CONTROLLED_METHOD,
    CALL_CTRL_DAGGERED_METHOD,
    CALL_CTRL_POWER_DAGGERED_METHOD,
    CALL_CTRL_POWERED_METHOD,
    CALL_DAGGERED_METHOD,
    CALL_POWER_DAGGERED_METHOD,
    CALL_POWERED_METHOD,
)


class CustomModifierKind(Enum):
    """Kinds of custom implementations supported by ``@guppy.unitary``."""

    DAGGERED = CALL_DAGGERED_METHOD
    CONTROLLED = CALL_CONTROLLED_METHOD
    CTRL_DAGGERED = CALL_CTRL_DAGGERED_METHOD
    POWERED = CALL_POWERED_METHOD
    POWER_DAGGERED = CALL_POWER_DAGGERED_METHOD
    CTRL_POWERED = CALL_CTRL_POWERED_METHOD
    CTRL_POWER_DAGGERED = CALL_CTRL_POWER_DAGGERED_METHOD

    @property
    def takes_controls(self) -> bool:
        """Whether the implementation has a control-count parameter."""
        return self in {
            CustomModifierKind.CONTROLLED,
            CustomModifierKind.CTRL_DAGGERED,
            CustomModifierKind.CTRL_POWERED,
            CustomModifierKind.CTRL_POWER_DAGGERED,
        }

    @property
    def takes_power(self) -> bool:
        """Whether the implementation takes a final runtime exponent."""
        return self in {
            CustomModifierKind.POWERED,
            CustomModifierKind.POWER_DAGGERED,
            CustomModifierKind.CTRL_POWERED,
            CustomModifierKind.CTRL_POWER_DAGGERED,
        }


@dataclass(frozen=True)
class ModifierContext:
    """Modifiers active at a call site; power exponents remain runtime values."""

    daggered: bool = False
    control_sizes: tuple[int | Const, ...] = ()
    powered: bool = False
    #: Power may be dispatched to a custom method only for a single-call block.
    power_customizable: bool = False

    def compose(self, inner: "ModifierContext") -> "ModifierContext":
        """Compose this modifier context with an inner context."""
        return ModifierContext(
            daggered=self.daggered ^ inner.daggered,
            control_sizes=(*self.control_sizes, *inner.control_sizes),
            powered=self.powered or inner.powered,
            power_customizable=(self.power_customizable or inner.power_customizable),
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
        if self.powered and self.power_customizable:
            if self.daggered and self.control_sizes:
                return CustomModifierKind.CTRL_POWER_DAGGERED
            if self.daggered:
                return CustomModifierKind.POWER_DAGGERED
            if self.control_sizes:
                return CustomModifierKind.CTRL_POWERED
            return CustomModifierKind.POWERED
        if self.daggered and self.control_sizes:
            return CustomModifierKind.CTRL_DAGGERED
        if self.daggered:
            return CustomModifierKind.DAGGERED
        if self.control_sizes:
            return CustomModifierKind.CONTROLLED
        return None


NO_CALL_MODIFIERS = ModifierContext()
