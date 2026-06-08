"""Shared types and helpers for qsystem platforms.

These definitions are platform-agnostic and are re-exported by both
``guppylang.std.qsystem.helios`` and ``guppylang.std.qsystem.sol``.
"""

from typing import no_type_check

from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.std._internal.compiler.qsystem import (
    ReadFutureBoolCompiler,
    future_bool_type,
)

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.futures import Future
from guppylang.std.option import Option, nothing, some

_N = guppy.nat_var("_N")


@custom_type(
    future_bool_type(),
    copyable=False,
    droppable=False,
)
class Measurement:
    """Represents the result of a lazy measurement which needs to be explicitly read
    before being used."""

    @custom_function(compiler=ReadFutureBoolCompiler())
    @no_type_check
    def read(self: "Measurement" @ owned) -> bool:
        """Read the measurement result, consuming it. Blocks until the result is
        available if the measurement hasn't been performed yet since being requested.
        """

    @guppy
    @no_type_check
    def __consume_as_bool__(self: "Measurement" @ owned) -> bool:
        return self.read()


@guppy.struct(frozen=True)
@no_type_check
class MaybeLeaked:  # type: ignore[misc]  # Error for Python < 3.13
    """A class representing a measurement that may have leaked.

    This is used to represent the result of ``measure_leaked``, which can either
    return a boolean measurement result or indicate that the qubit has leaked.
    """

    _measurement: Future[int]  # type: ignore[type-arg]

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
