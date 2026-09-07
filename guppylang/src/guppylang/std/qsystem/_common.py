"""Shared types and helpers for qsystem platforms.

These definitions are platform-agnostic and should be reexported by all
platforms (e.g. ``guppylang.std.qsystem.helios`` and ``guppylang.std.qsystem.sol``).
"""

from typing import no_type_check

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.futures import Future
from guppylang.std.option import Option, nothing, some
from guppylang.std.quantum import Measurement

_N = guppy.nat_var("_N")


@guppy.struct(frozen=True)
@no_type_check
class MaybeLeaked:  # type: ignore[misc]  # Error for Python < 3.13
    """A class representing a measurement that may have leaked.

    This is used to represent the result of ``measure_leaked``, which can either
    return a boolean measurement result or indicate that the qubit has leaked.
    """

    _measurement: Future[int]

    @guppy
    @no_type_check
    def is_leaked(self: "MaybeLeaked") -> bool:
        """Check if the measurement indicates a leak."""
        return self._measurement.copy().read() == 2

    @guppy
    @no_type_check
    def to_result(self: "MaybeLeaked @ owned") -> Option[bool]:
        """Returns the measurement result or ``nothing`` if leaked."""
        int_value: int = self._measurement.read()
        if int_value == 2:
            return nothing()
        measurement = int_value == 1
        return some(measurement)

    @guppy
    @no_type_check
    def discard(self: "MaybeLeaked @ owned") -> None:
        self._measurement.discard()


@guppy
@no_type_check
def collect_measurements(
    measurements: array[Measurement, _N] @ owned,
) -> array[bool, _N]:
    """Block on each measurement until it is available and collect results into an
    array of bools.
    """
    return array(m.read() for m in measurements)
