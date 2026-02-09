"""Guppy standard module for functional quantum operations. For the mathematical
definitions of these gates, see the guppylang.std.quantum documentation.

These gates are the same as those in std.quantum but use functional syntax.
"""

from typing import no_type_check

import guppylang.std.quantum as quantum
from guppylang.decorator import guppy

# mypy: disable-error-code="empty-body, misc, valid-type, no-untyped-def"
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.quantum import qubit

N = guppy.nat_var("N")


# ---------------------------------------------------------------------------
# Single-qubit gates (scalar + array overloads)
# ---------------------------------------------------------------------------


@guppy
@no_type_check
def _h(q: qubit @ owned) -> qubit:
    quantum.h(q)
    return q


@guppy
@no_type_check
def _h_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.h(qs[i])
    return qs


@guppy.overload(_h, _h_array)
def h(q):
    """Functional Hadamard gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _t(q: qubit @ owned) -> qubit:
    quantum.t(q)
    return q


@guppy
@no_type_check
def _t_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.t(qs[i])
    return qs


@guppy.overload(_t, _t_array)
def t(q):
    """Functional T gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _s(q: qubit @ owned) -> qubit:
    quantum.s(q)
    return q


@guppy
@no_type_check
def _s_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.s(qs[i])
    return qs


@guppy.overload(_s, _s_array)
def s(q):
    """Functional S gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _v(q: qubit @ owned) -> qubit:
    quantum.v(q)
    return q


@guppy
@no_type_check
def _v_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.v(qs[i])
    return qs


@guppy.overload(_v, _v_array)
def v(q):
    """Functional V gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _x(q: qubit @ owned) -> qubit:
    quantum.x(q)
    return q


@guppy
@no_type_check
def _x_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.x(qs[i])
    return qs


@guppy.overload(_x, _x_array)
def x(q):
    """Functional X gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _y(q: qubit @ owned) -> qubit:
    quantum.y(q)
    return q


@guppy
@no_type_check
def _y_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.y(qs[i])
    return qs


@guppy.overload(_y, _y_array)
def y(q):
    """Functional Y gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _z(q: qubit @ owned) -> qubit:
    quantum.z(q)
    return q


@guppy
@no_type_check
def _z_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.z(qs[i])
    return qs


@guppy.overload(_z, _z_array)
def z(q):
    """Functional Z gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _tdg(q: qubit @ owned) -> qubit:
    quantum.tdg(q)
    return q


@guppy
@no_type_check
def _tdg_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.tdg(qs[i])
    return qs


@guppy.overload(_tdg, _tdg_array)
def tdg(q):
    """Functional Tdg gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _sdg(q: qubit @ owned) -> qubit:
    quantum.sdg(q)
    return q


@guppy
@no_type_check
def _sdg_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.sdg(qs[i])
    return qs


@guppy.overload(_sdg, _sdg_array)
def sdg(q):
    """Functional Sdg gate command. Accepts a single qubit or an array."""


@guppy
@no_type_check
def _vdg(q: qubit @ owned) -> qubit:
    quantum.vdg(q)
    return q


@guppy
@no_type_check
def _vdg_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.vdg(qs[i])
    return qs


@guppy.overload(_vdg, _vdg_array)
def vdg(q):
    """Functional Vdg gate command. Accepts a single qubit or an array."""


# ---------------------------------------------------------------------------
# Rotation gates (no array overloads for now)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Two-qubit gates (scalar + array overloads)
# ---------------------------------------------------------------------------


@guppy
@no_type_check
def _cz(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.cz(control, target)
    return control, target


@guppy
@no_type_check
def _cz_array(
    controls: array[qubit, N] @ owned, targets: array[qubit, N] @ owned
) -> tuple[array[qubit, N], array[qubit, N]]:
    for i in range(N):
        quantum.cz(controls[i], targets[i])
    return controls, targets


@guppy.overload(_cz, _cz_array)
def cz(control, target):
    """Functional CZ gate command. Accepts single qubits or arrays."""


@guppy
@no_type_check
def _cx(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.cx(control, target)
    return control, target


@guppy
@no_type_check
def _cx_array(
    controls: array[qubit, N] @ owned, targets: array[qubit, N] @ owned
) -> tuple[array[qubit, N], array[qubit, N]]:
    for i in range(N):
        quantum.cx(controls[i], targets[i])
    return controls, targets


@guppy.overload(_cx, _cx_array)
def cx(control, target):
    """Functional CX gate command. Accepts single qubits or arrays."""


@guppy
@no_type_check
def _cy(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.cy(control, target)
    return control, target


@guppy
@no_type_check
def _cy_array(
    controls: array[qubit, N] @ owned, targets: array[qubit, N] @ owned
) -> tuple[array[qubit, N], array[qubit, N]]:
    for i in range(N):
        quantum.cy(controls[i], targets[i])
    return controls, targets


@guppy.overload(_cy, _cy_array)
def cy(control, target):
    """Functional CY gate command. Accepts single qubits or arrays."""


# ---------------------------------------------------------------------------
# Other gates (no array overloads)
# ---------------------------------------------------------------------------


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
def _reset(q: qubit @ owned) -> qubit:
    quantum.reset(q)
    return q


@guppy
@no_type_check
def _reset_array(qs: array[qubit, N] @ owned) -> array[qubit, N]:
    for i in range(N):
        quantum.reset(qs[i])
    return qs


@guppy.overload(_reset, _reset_array)
def reset(q):
    """Functional Reset command. Accepts a single qubit or an array."""


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
