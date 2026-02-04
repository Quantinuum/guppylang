"""Guppy standard module for functional qsystem native operations. For the mathematical
definitions of these gates, see the guppylang.std.qsystem documentation.

These gates are the same as those in std.qsystem but use functional syntax.
"""

from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.std import qsystem
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


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
def measure_and_reset(q: qubit @ owned) -> tuple[qubit, bool]:
    """Functional measure_and_reset command."""
    b = qsystem.measure_and_reset(q)
    return q, b


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
def measure(q: qubit @ owned) -> bool:
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
