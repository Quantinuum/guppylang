"""Functional wrappers for Quantinuum Sol system operations.

These gates are the same as those in ``guppylang.std.qsystem.sol`` but use
functional syntax (owned qubits are taken and returned rather than borrowed).
"""

from typing import no_type_check

import guppylang.std.qsystem.sol as sol
from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.quantum import Measurement, qubit

N = guppy.nat_var("N")


@guppy
@no_type_check
def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
    """Functional PhasedX gate command."""
    sol.phased_x(q, angle1, angle2)
    return q


@guppy
@no_type_check
def phased_xx(
    q1: qubit @ owned, q2: qubit @ owned, angle1: angle, angle2: angle
) -> tuple[qubit, qubit]:
    """Functional PhasedXX gate command. The native 2-qubit entangling gate on Sol."""
    sol.phased_xx(q1, q2, angle1, angle2)
    return q1, q2


@guppy
@no_type_check
def phased_xx_max(
    q1: qubit @ owned, q2: qubit @ owned, phase: angle
) -> tuple[qubit, qubit]:
    """Functional phased_xx_max gate command.

    Maximally entangling PhasedXX gate at a given phase.
    """
    sol.phased_xx_max(q1, q2, phase)
    return q1, q2


@guppy
@no_type_check
def xx_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional xx_max gate command. Maximally entangling XX gate."""
    sol.xx_max(q1, q2)
    return q1, q2


@guppy
@no_type_check
def rz(q: qubit @ owned, angle: angle) -> qubit:
    """Functional Rz gate command."""
    sol.rz(q, angle)
    return q


@guppy
@no_type_check
def measure(q: qubit @ owned) -> Measurement:
    """Functional measurement command."""
    return sol.measure(q)


@guppy
@no_type_check
def measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
    """Functional measure_and_reset command."""
    b = sol.measure_and_reset(q)
    return q, b


@guppy
@no_type_check
def reset(q: qubit @ owned) -> qubit:
    """Functional Reset command."""
    sol.reset(q)
    return q


@guppy
@no_type_check
def qfree(q: qubit @ owned) -> None:
    """Functional qfree command."""
    sol.qfree(q)


@guppy
@no_type_check
def lazy_measure_and_reset(q: qubit @ owned) -> tuple[qubit, Measurement]:
    """Functional lazy_measure_and_reset command."""
    measurement = sol.lazy_measure_and_reset(q)
    return q, measurement


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[Measurement, N]:
    """Functional measure_array command."""
    return sol.measure_array(qubits)


@guppy
@no_type_check
def measure_and_reset_array(
    qubits: array[qubit, N] @ owned,
) -> tuple[array[qubit, N], array[Measurement, N]]:
    """Functional measure_and_reset_array command."""
    bs = sol.measure_and_reset_array(qubits)
    return qubits, bs


@guppy
@no_type_check
def lazy_measure_and_reset_array(
    qubits: array[qubit, N] @ owned,
) -> tuple[array[qubit, N], array[Measurement, N]]:
    """Functional lazy_measure_and_reset_array command."""
    measurements = sol.lazy_measure_and_reset_array(qubits)
    return qubits, measurements
