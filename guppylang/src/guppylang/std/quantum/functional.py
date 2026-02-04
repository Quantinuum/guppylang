"""Guppy standard module for functional quantum operations. For the mathematical
definitions of these gates, see the guppylang.std.quantum documentation.

These gates are the same as those in std.quantum but use functional syntax.
"""

from typing import no_type_check

import guppylang.std.quantum as quantum
from guppylang.decorator import guppy

# mypy: disable-error-code="empty-body, misc, valid-type"
from guppylang.std.angles import angle
from guppylang.std.lang import owned
from guppylang.std.quantum import qubit


@guppy
@no_type_check
def h(q: qubit @ owned) -> qubit:
    """Functional Hadamard gate command."""
    quantum.h(q)
    return q


@guppy
@no_type_check
def cz(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional CZ gate command."""
    quantum.cz(control, target)
    return control, target


@guppy
@no_type_check
def cx(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional CX gate command."""
    quantum.cx(control, target)
    return control, target


@guppy
@no_type_check
def cy(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional CY gate command."""
    quantum.cy(control, target)
    return control, target


@guppy
@no_type_check
def t(q: qubit @ owned) -> qubit:
    """Functional T gate command."""
    quantum.t(q)
    return q


@guppy
@no_type_check
def s(q: qubit @ owned) -> qubit:
    """Functional S gate command."""
    quantum.s(q)
    return q


@guppy
@no_type_check
def v(q: qubit @ owned) -> qubit:
    """Functional V gate command."""
    quantum.v(q)
    return q


@guppy
@no_type_check
def x(q: qubit @ owned) -> qubit:
    """Functional X gate command."""
    quantum.x(q)
    return q


@guppy
@no_type_check
def y(q: qubit @ owned) -> qubit:
    """Functional Y gate command."""
    quantum.y(q)
    return q


@guppy
@no_type_check
def z(q: qubit @ owned) -> qubit:
    """Functional Z gate command."""
    quantum.z(q)
    return q


@guppy
@no_type_check
def tdg(q: qubit @ owned) -> qubit:
    """Functional Tdg gate command."""
    quantum.tdg(q)
    return q


@guppy
@no_type_check
def sdg(q: qubit @ owned) -> qubit:
    """Functional Sdg gate command."""
    quantum.sdg(q)
    return q


@guppy
@no_type_check
def vdg(q: qubit @ owned) -> qubit:
    """Functional Vdg gate command."""
    quantum.vdg(q)
    return q


@guppy
@no_type_check
def rz(q: qubit @ owned, angle: angle) -> qubit:
    """Functional Rz gate command."""
    quantum.rz(q, angle)
    return q


@guppy
@no_type_check
def rx(q: qubit @ owned, angle: angle) -> qubit:
    """Functional Rx gate command."""
    quantum.rx(q, angle)
    return q


@guppy
@no_type_check
def ry(q: qubit @ owned, angle: angle) -> qubit:
    """Functional Ry gate command."""
    quantum.ry(q, angle)
    return q


@guppy
@no_type_check
def crz(
    control: qubit @ owned, target: qubit @ owned, angle: angle
) -> tuple[qubit, qubit]:
    """Functional CRz gate command."""
    quantum.crz(control, target, angle)
    return control, target


@guppy
@no_type_check
def toffoli(
    control1: qubit @ owned, control2: qubit @ owned, target: qubit @ owned
) -> tuple[qubit, qubit, qubit]:
    """Functional Toffoli gate command."""
    quantum.toffoli(control1, control2, target)
    return control1, control2, target


@guppy
@no_type_check
def reset(q: qubit @ owned) -> qubit:
    """Functional Reset command."""
    quantum.reset(q)
    return q


@guppy
@no_type_check
def project_z(q: qubit @ owned) -> tuple[qubit, bool]:
    """Functional project_z command."""
    b = quantum.project_z(q)
    return q, b


# -------NON-PRIMITIVE-------


@guppy
@no_type_check
def ch(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional Controlled-H gate command."""
    quantum.ch(control, target)
    return control, target
