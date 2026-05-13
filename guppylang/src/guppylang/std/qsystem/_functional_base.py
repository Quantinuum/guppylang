"""Factory for shared functional wrappers across qsystem platforms.

Both ``guppylang.std.qsystem.helios.functional`` and
``guppylang.std.qsystem.sol.functional`` use this factory to generate the ops
that are common to all platforms, avoiding duplication.
"""

from types import ModuleType
from typing import Any, TypedDict, no_type_check

from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.quantum import Measurement, qubit


class SharedFunctionalVariants(TypedDict):
    phased_x: Any
    rz: Any
    measure: Any
    reset: Any
    qfree: Any
    measure_and_reset: Any
    lazy_measure_and_reset: Any
    measure_array: Any
    measure_and_reset_array: Any
    lazy_measure_and_reset_array: Any


def _make_shared_functional(platform: ModuleType) -> SharedFunctionalVariants:
    """Return shared functional wrapper definitions for a qsystem platform module.

    ``platform`` should be either ``guppylang.std.qsystem.helios`` or
    ``guppylang.std.qsystem.sol``.  The returned dict maps function names to
    ``GuppyDefinition`` objects that can be assigned directly in the calling
    module's namespace.
    """
    N = guppy.nat_var("N")

    @guppy
    @no_type_check
    def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
        """Functional PhasedX gate command."""
        platform.phased_x(q, angle1, angle2)
        return q

    @guppy
    @no_type_check
    def rz(q: qubit @ owned, angle: angle) -> qubit:
        """Functional Rz gate command."""
        platform.rz(q, angle)
        return q

    @guppy
    @no_type_check
    def measure(q: qubit @ owned) -> Measurement:
        """Functional destructive measurement command."""
        return platform.measure(q)

    @guppy
    @no_type_check
    def measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
        """Functional measure_and_reset command."""
        b = platform.measure_and_reset(q)
        return q, b

    @guppy
    @no_type_check
    def reset(q: qubit @ owned) -> qubit:
        """Functional Reset command."""
        platform.reset(q)
        return q

    @guppy
    @no_type_check
    def qfree(q: qubit @ owned) -> None:
        """Functional qfree command."""
        platform.qfree(q)

    @guppy
    @no_type_check
    def lazy_measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
        """Functional lazy_measure_and_reset command."""
        measurement = platform.lazy_measure_and_reset(q)
        return q, measurement

    @guppy
    @no_type_check
    def measure_array(qubits: array[qubit, N] @ owned) -> array[Measurement, N]:
        """Functional measure_array command."""
        return platform.measure_array(qubits)

    @guppy
    @no_type_check
    def measure_and_reset_array(
        qubits: array[qubit, N] @ owned,
    ) -> tuple[array[qubit, N], array[Measurement, N]]:
        """Functional measure_and_reset_array command."""
        bs = platform.measure_and_reset_array(qubits)
        return qubits, bs

    @guppy
    @no_type_check
    def lazy_measure_and_reset_array(
        qubits: array[qubit, N] @ owned,
    ) -> tuple[array[qubit, N], array[Measurement, N]]:
        """Functional lazy_measure_and_reset_array command."""
        measurements = platform.lazy_measure_and_reset_array(qubits)
        return qubits, measurements

    return {
        "phased_x": phased_x,
        "rz": rz,
        "measure": measure,
        "measure_and_reset": measure_and_reset,
        "reset": reset,
        "qfree": qfree,
        "lazy_measure_and_reset": lazy_measure_and_reset,
        "measure_array": measure_array,
        "measure_and_reset_array": measure_and_reset_array,
        "lazy_measure_and_reset_array": lazy_measure_and_reset_array,
    }
