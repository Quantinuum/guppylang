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
from guppylang.std.quantum import AbstractQubit, Measurement


@guppy
@no_type_check
def h[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Hadamard gate command."""
    quantum.h(q)
    return q


@guppy
@no_type_check
def cz[Q: AbstractQubit](control: Q @ owned, target: Q @ owned) -> tuple[Q, Q]:
    """Functional CZ gate command."""
    quantum.cz(control, target)
    return control, target


@guppy
@no_type_check
def cx[Q: AbstractQubit](control: Q @ owned, target: Q @ owned) -> tuple[Q, Q]:
    """Functional CX gate command."""
    quantum.cx(control, target)
    return control, target


@guppy
@no_type_check
def cy[Q: AbstractQubit](control: Q @ owned, target: Q @ owned) -> tuple[Q, Q]:
    """Functional CY gate command."""
    quantum.cy(control, target)
    return control, target


@guppy
@no_type_check
def t[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional T gate command."""
    quantum.t(q)
    return q


@guppy
@no_type_check
def s[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional S gate command."""
    quantum.s(q)
    return q


@guppy
@no_type_check
def v[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional V gate command."""
    quantum.v(q)
    return q


@guppy
@no_type_check
def x[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional X gate command."""
    quantum.x(q)
    return q


@guppy
@no_type_check
def y[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Y gate command."""
    quantum.y(q)
    return q


@guppy
@no_type_check
def z[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Z gate command."""
    quantum.z(q)
    return q


@guppy
@no_type_check
def tdg[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Tdg gate command."""
    quantum.tdg(q)
    return q


@guppy
@no_type_check
def sdg[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Sdg gate command."""
    quantum.sdg(q)
    return q


@guppy
@no_type_check
def vdg[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Vdg gate command."""
    quantum.vdg(q)
    return q


@guppy
@no_type_check
def rz[Q: AbstractQubit](q: Q @ owned, angle: angle) -> Q:
    """Functional Rz gate command."""
    quantum.rz(q, angle)
    return q


@guppy
@no_type_check
def rx[Q: AbstractQubit](q: Q @ owned, angle: angle) -> Q:
    """Functional Rx gate command."""
    quantum.rx(q, angle)
    return q


@guppy
@no_type_check
def ry[Q: AbstractQubit](q: Q @ owned, angle: angle) -> Q:
    """Functional Ry gate command."""
    quantum.ry(q, angle)
    return q


@guppy
@no_type_check
def crz[Q: AbstractQubit](
    control: Q @ owned, target: Q @ owned, angle: angle
) -> tuple[Q, Q]:
    """Functional CRz gate command."""
    quantum.crz(control, target, angle)
    return control, target


@guppy
@no_type_check
def toffoli[Q: AbstractQubit](
    control1: Q @ owned, control2: Q @ owned, target: Q @ owned
) -> tuple[Q, Q, Q]:
    """Functional Toffoli gate command."""
    quantum.toffoli(control1, control2, target)
    return control1, control2, target


@guppy
@no_type_check
def reset[Q: AbstractQubit](q: Q @ owned) -> Q:
    """Functional Reset command."""
    quantum.reset(q)
    return q


@guppy
@no_type_check
def project_z[Q: AbstractQubit](q: Q @ owned) -> tuple[Q, Measurement]:
    """Functional project_z command."""
    b = quantum.project_z(q)
    return q, b


# -------NON-PRIMITIVE-------


@guppy
@no_type_check
def ch[Q: AbstractQubit](control: Q @ owned, target: Q @ owned) -> tuple[Q, Q]:
    """Functional Controlled-H gate command."""
    quantum.ch(control, target)
    return control, target
