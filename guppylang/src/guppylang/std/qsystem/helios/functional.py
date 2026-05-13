"""Functional wrappers for Quantinuum Helios system operations.

These gates are the same as those in ``guppylang.std.qsystem.helios`` but use
functional syntax (owned qubits are taken and returned rather than borrowed).
"""

from typing import no_type_check

import guppylang.std.qsystem.helios as helios
from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.qsystem._common import Measurement
from guppylang.std.quantum import qubit

N = guppy.nat_var("N")


@guppy
@no_type_check
def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
    """Functional PhasedX gate command."""
    helios.phased_x(q, angle1, angle2)
    return q


@guppy
@no_type_check
def zz_phase(q1: qubit @ owned, q2: qubit @ owned, angle: angle) -> tuple[qubit, qubit]:
    """Functional ZZPhase gate command."""
    helios.zz_phase(q1, q2, angle)
    return q1, q2


@guppy
@no_type_check
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional ZZMax gate command."""
    helios.zz_max(q1, q2)
    return q1, q2


@guppy
@no_type_check
def rz(q: qubit @ owned, angle: angle) -> qubit:
    """Functional Rz gate command."""
    helios.rz(q, angle)
    return q


@guppy
@no_type_check
def measure(q: qubit @ owned) -> bool:
    """Functional destructive measurement command."""
    return helios.measure(q)


@guppy
@no_type_check
def measure_and_reset(q: qubit @ owned) -> tuple[qubit, bool]:
    """Functional measure_and_reset command."""
    b = helios.measure_and_reset(q)
    return q, b


@guppy
@no_type_check
def reset(q: qubit @ owned) -> qubit:
    """Functional Reset command."""
    helios.reset(q)
    return q


@guppy
@no_type_check
def qfree(q: qubit @ owned) -> None:
    """Functional qfree command."""
    helios.qfree(q)


@guppy
@no_type_check
def lazy_measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
    """Functional lazy_measure_and_reset command."""
    measurement = helios.lazy_measure_and_reset(q)
    return q, measurement


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[bool, N]:
    """Functional measure_array command."""
    return helios.measure_array(qubits)


@guppy
@no_type_check
def measure_and_reset_array(
    qubits: array[qubit, N] @ owned,
) -> tuple[array[qubit, N], array[bool, N]]:
    """Functional measure_and_reset_array command."""
    bs = helios.measure_and_reset_array(qubits)
    return qubits, bs


@guppy
@no_type_check
def lazy_measure_and_reset_array(
    qubits: array[qubit, N] @ owned,
) -> tuple[array[qubit, N], array[Measurement, N]]:
    """Functional lazy_measure_and_reset_array command."""
    measurements = helios.lazy_measure_and_reset_array(qubits)
    return qubits, measurements
