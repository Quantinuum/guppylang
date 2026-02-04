"""Guppy standard module for dyadic rational angles."""

# mypy: disable-error-code="empty-body, misc, override, operator"

import math
from typing import no_type_check

from hugr import val as hv
from hugr.std.float import FloatVal

from guppylang.decorator import guppy
from guppylang.std.builtins import py


@guppy.struct
class angle:
    """Not an angle in the truest sense but a rotation by a number of half-turns
    (does not wrap or identify with itself modulo any number of complete turns).
    """

    halfturns: float

    @guppy
    @no_type_check
    def __add__(self: "angle", other: "angle") -> "angle":
        return angle(self.halfturns + other.halfturns)

    @guppy
    @no_type_check
    def __sub__(self: "angle", other: "angle") -> "angle":
        return angle(self.halfturns - other.halfturns)

    @guppy
    @no_type_check
    def __mul__(self: "angle", other: float) -> "angle":
        return angle(self.halfturns * other)

    @guppy
    @no_type_check
    def __rmul__(self: "angle", other: float) -> "angle":
        return angle(self.halfturns * other)

    @guppy
    @no_type_check
    def __truediv__(self: "angle", other: float) -> "angle":
        return angle(self.halfturns / other)

    @guppy
    @no_type_check
    def __rtruediv__(self: "angle", other: float) -> "angle":
        return angle(other / self.halfturns)

    @guppy
    @no_type_check
    def __neg__(self: "angle") -> "angle":
        return angle(-self.halfturns)

    @guppy
    @no_type_check
    def __float__(self: "angle") -> float:
        return self.halfturns * py(math.pi)

    @guppy
    @no_type_check
    def __eq__(self: "angle", other: "angle") -> bool:
        return self.halfturns == other.halfturns


pi: angle = guppy.constant("pi", ty="angle", value=hv.Tuple(FloatVal(1.0)))
