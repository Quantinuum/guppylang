"""Guppy standard module for functional qsystem native operations. For the mathematical
definitions of these gates, see the guppylang.std.qsystem documentation.

These gates are the same as those in std.qsystem but use functional syntax.
"""

from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.std import qsystem
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.quantum import Measurement, qubit

N = guppy.nat_var("N")


@guppy
@no_type_check
def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
    """Functional PhasedX gate command."""
    qsystem.phased_x(q, angle1, angle2)
    return q


@guppy
@no_type_check
def zz_phase(q1: qubit @ owned, q2: qubit @ owned, angle: angle) -> tuple[qubit, qubit]:
    """Functional ZZPhase gate command."""
    qsystem.zz_phase(q1, q2, angle)
    return q1, q2


@guppy
@no_type_check
def measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
    """Functional measure_and_reset command."""
    b = qsystem.measure_and_reset(q)
    return q, b


@guppy
@no_type_check
def lazy_measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
    """Functional lazy_measure_and_reset command."""
    measurement = qsystem.lazy_measure_and_reset(q)
    return q, measurement


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[Measurement, N]:
    """Functional measure_array command."""
    return qsystem.measure_array(qubits)


@guppy
@no_type_check
def measure_and_reset_array(
    qubits: array[qubit, N] @ owned,
) -> tuple[array[qubit, N], array[bool, N]]:
    """Functional measure_and_reset_array command."""
    bs = qsystem.measure_and_reset_array(qubits)
    return qubits, bs


@guppy
@no_type_check
def lazy_measure_and_reset_array(
    qubits: array[qubit, N] @ owned,
) -> tuple[array[qubit, N], array[Measurement, N]]:
    """Functional lazy_measure_and_reset_array command."""
    measurements = qsystem.lazy_measure_and_reset_array(qubits)
    return qubits, measurements


@guppy
@no_type_check
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional ZZMax gate command."""
    qsystem.zz_max(q1, q2)
    return q1, q2


@guppy
@no_type_check
def rz(q: qubit @ owned, angle: angle) -> qubit:
    """Functional Rz gate command."""
    qsystem.rz(q, angle)
    return q


@guppy
@no_type_check
def measure(q: qubit @ owned) -> Measurement:
    """Functional destructive measurement command."""
    result = qsystem.measure(q)
    return result


@guppy
@no_type_check
def qfree(q: qubit @ owned) -> None:
    """Functional qfree command."""
    qsystem.qfree(q)


@guppy
@no_type_check
def reset(q: qubit @ owned) -> qubit:
    """Functional Reset command."""
    qsystem.reset(q)
    return q
