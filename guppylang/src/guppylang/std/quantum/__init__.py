"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc, valid-type"

from typing import no_type_check

from guppylang_internals.decorator import custom_function, custom_type, hugr_op
from guppylang_internals.std._internal.compiler.quantum import (
    InoutMeasureCompiler,
    RotationCompiler,
)
from guppylang_internals.std._internal.util import quantum_op
from guppylang_internals.tys.ty import UnitaryFlags
from hugr import tys as ht

from guppylang import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.option import Option


@custom_type(ht.Qubit, copyable=False, droppable=False)
class qubit:
    @hugr_op(quantum_op("QAlloc"))
    @no_type_check
    def __new__() -> "qubit": ...

    @guppy
    @no_type_check
    def measure(self: "qubit" @ owned) -> bool:
        return measure(self)

    @guppy
    @no_type_check
    def project_z(self: "qubit") -> bool:
        return project_z(self)

    @guppy
    @no_type_check
    def discard(self: "qubit" @ owned) -> None:
        discard(self)


@hugr_op(quantum_op("TryQAlloc"))
@no_type_check
def maybe_qubit() -> Option[qubit]:
    """Try to allocate a qubit, returning `some(qubit)`
    if allocation succeeds or `nothing` if it fails."""


N = guppy.nat_var("N")


@hugr_op(quantum_op("H"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _h(q: qubit) -> None: ...


@guppy
@no_type_check
def _h_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _h(qs[i])


@guppy.overload(_h, _h_array)
@no_type_check
def h(q) -> None:
    r"""Hadamard gate command. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{H}= \frac{1}{\sqrt{2}}
          \begin{pmatrix}
            1 & 1 \\
            1 & -1
          \end{pmatrix}
    """


@hugr_op(quantum_op("CZ"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _cz(control: qubit, target: qubit) -> None: ...


@guppy
@no_type_check
def _cz_array(controls: array[qubit, N], targets: array[qubit, N]) -> None:
    for i in range(N):
        _cz(controls[i], targets[i])


@guppy.overload(_cz, _cz_array)
@no_type_check
def cz(control, target) -> None:
    r"""Controlled-Z gate command. Accepts single qubits or arrays of qubits.

    cz(control, target)

    Qubit ordering: [control, target]

    .. math::
        \mathrm{CZ}=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 1 & 0 \\
            0 & 0 & 0 & -1
          \end{pmatrix}
    """


@hugr_op(quantum_op("CY"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _cy(control: qubit, target: qubit) -> None: ...


@guppy
@no_type_check
def _cy_array(controls: array[qubit, N], targets: array[qubit, N]) -> None:
    for i in range(N):
        _cy(controls[i], targets[i])


@guppy.overload(_cy, _cy_array)
@no_type_check
def cy(control, target) -> None:
    r"""Controlled-Y gate command. Accepts single qubits or arrays of qubits.

    cy(control, target)

    Qubit ordering: [control, target]

    .. math::
        \mathrm{CY}=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 0 & -i \\
            0 & 0 & i & 0
          \end{pmatrix}
    """


@hugr_op(quantum_op("CX"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _cx(control: qubit, target: qubit) -> None: ...


@guppy
@no_type_check
def _cx_array(controls: array[qubit, N], targets: array[qubit, N]) -> None:
    for i in range(N):
        _cx(controls[i], targets[i])


@guppy.overload(_cx, _cx_array)
@no_type_check
def cx(control, target) -> None:
    r"""Controlled-X gate command. Accepts single qubits or arrays of qubits.

    cx(control, target)

    Qubit ordering: [control, target]

    .. math::
        \mathrm{CX}=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 0 & 1 \\
            0 & 0 & 1 & 0
          \end{pmatrix}
    """


@hugr_op(quantum_op("T"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _t(q: qubit) -> None: ...


@guppy
@no_type_check
def _t_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _t(qs[i])


@guppy.overload(_t, _t_array)
@no_type_check
def t(q) -> None:
    r"""T gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{T}=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{i \frac{\pi}{4}}
           \end{pmatrix}

    """


@hugr_op(quantum_op("S"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _s(q: qubit) -> None: ...


@guppy
@no_type_check
def _s_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _s(qs[i])


@guppy.overload(_s, _s_array)
@no_type_check
def s(q) -> None:
    r"""S gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{S}=
          \begin{pmatrix}
            1 & 0 \\
            0 & i
           \end{pmatrix}

    """


@hugr_op(quantum_op("V"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _v(q: qubit) -> None: ...


@guppy
@no_type_check
def _v_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _v(qs[i])


@guppy.overload(_v, _v_array)
@no_type_check
def v(q) -> None:
    r"""V gate. Accepts a single qubit or an array of qubits.

    .. math::
      \mathrm{V}= \frac{1}{\sqrt{2}}
       \begin{pmatrix}
            1 & -i \\
            -i & 1
           \end{pmatrix}

    """


@hugr_op(quantum_op("X"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _x(q: qubit) -> None: ...


@guppy
@no_type_check
def _x_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _x(qs[i])


@guppy.overload(_x, _x_array)
@no_type_check
def x(q) -> None:
    r"""X gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{X}=
          \begin{pmatrix}
            0 & 1 \\
            1 & 0
           \end{pmatrix}

    """


@hugr_op(quantum_op("Y"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _y(q: qubit) -> None: ...


@guppy
@no_type_check
def _y_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _y(qs[i])


@guppy.overload(_y, _y_array)
@no_type_check
def y(q) -> None:
    r"""Y gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{Y}=
          \begin{pmatrix}
            0 & -i \\
            i & 0
           \end{pmatrix}

    """


@hugr_op(quantum_op("Z"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _z(q: qubit) -> None: ...


@guppy
@no_type_check
def _z_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _z(qs[i])


@guppy.overload(_z, _z_array)
@no_type_check
def z(q) -> None:
    r"""Z gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{Z}=
          \begin{pmatrix}
            1 & 0 \\
            0 & -1
           \end{pmatrix}

    """


@hugr_op(quantum_op("Tdg"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _tdg(q: qubit) -> None: ...


@guppy
@no_type_check
def _tdg_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _tdg(qs[i])


@guppy.overload(_tdg, _tdg_array)
@no_type_check
def tdg(q) -> None:
    r"""Tdg gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{T}^\dagger=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{-i \frac{\pi}{4}}
           \end{pmatrix}

    """


@hugr_op(quantum_op("Sdg"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _sdg(q: qubit) -> None: ...


@guppy
@no_type_check
def _sdg_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _sdg(qs[i])


@guppy.overload(_sdg, _sdg_array)
@no_type_check
def sdg(q) -> None:
    r"""Sdg gate. Accepts a single qubit or an array of qubits.

    .. math::
        \mathrm{S}^\dagger=
          \begin{pmatrix}
            1 & 0 \\
            0 & -i
           \end{pmatrix}

    """


@hugr_op(quantum_op("Vdg"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _vdg(q: qubit) -> None: ...


@guppy
@no_type_check
def _vdg_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _vdg(qs[i])


@guppy.overload(_vdg, _vdg_array)
@no_type_check
def vdg(q) -> None:
    r"""Vdg gate. Accepts a single qubit or an array of qubits.

    .. math::
      \mathrm{V}^\dagger= \frac{1}{\sqrt{2}}
       \begin{pmatrix}
            1 & i \\
            i & 1
           \end{pmatrix}

    """


@custom_function(RotationCompiler("Rz"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def rz(q: qubit, angle: angle) -> None:
    r"""Rz gate.

    .. math::
        \mathrm{Rz}(\theta)=
        \exp(\frac{- i  \theta}{2} Z)=
          \begin{pmatrix}
            e^{-\frac{1}{2}i  \theta} & 0 \\
            0 & e^{\frac{1}{2}i  \theta}
           \end{pmatrix}

    """


@custom_function(RotationCompiler("Rx"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def rx(q: qubit, angle: angle) -> None:
    r"""Rx gate.

    .. math::
        \mathrm{Rx}(\theta)=
          \begin{pmatrix}
            \cos(\frac{ \theta}{2}) & -i\sin(\frac{ \theta}{2}) \\
            -i\sin(\frac{ \theta}{2}) & \cos(\frac{ \theta}{2})
           \end{pmatrix}

    """


@custom_function(RotationCompiler("Ry"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def ry(q: qubit, angle: angle) -> None:
    r"""Ry gate.

    .. math::
        \mathrm{Ry}(\theta)=
          \begin{pmatrix}
            \cos(\frac{\theta}{2}) & -\sin(\frac{ \theta}{2}) \\
            \sin(\frac{ \theta}{2}) & \cos(\frac{ \theta}{2})
           \end{pmatrix}

    """


@custom_function(RotationCompiler("CRz"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def crz(control: qubit, target: qubit, angle: angle) -> None:
    r"""Controlled-Rz gate command.

    crz(control, target, theta)

    Qubit ordering: [control, target]

    .. math::
        \mathrm{CRz}(\theta)=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & e^{-\frac{1}{2}i  \theta} & 0 \\
            0 & 0 & 0 & e^{\frac{1}{2}i  \theta}
        \end{pmatrix}
    """


@hugr_op(quantum_op("Toffoli"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def toffoli(control1: qubit, control2: qubit, target: qubit) -> None:
    r"""A Toffoli gate command. Also sometimes known as a CCX gate.

    toffoli(control1, control2, target)

    Qubit ordering: [control1, control2 target]

    .. math::
        \mathrm{Toffoli}=
          \begin{pmatrix}
            1 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 & 0 & 0 & 0 & 0 \\
            0 & 0 & 1 & 0 & 0 & 0 & 0 & 0 \\
            0 & 0 & 0 & 1 & 0 & 0 & 0 & 0 \\
            0 & 0 & 0 & 0 & 1 & 0 & 0 & 0 \\
            0 & 0 & 0 & 0 & 0 & 1 & 0 & 0 \\
            0 & 0 & 0 & 0 & 0 & 0 & 0 & 1 \\
            0 & 0 & 0 & 0 & 0 & 0 & 1 & 0
          \end{pmatrix}
    """


@custom_function(InoutMeasureCompiler())
@no_type_check
def project_z(q: qubit) -> bool:
    """Project a single qubit into the Z-basis (a non-destructive measurement)."""


@hugr_op(quantum_op("QFree"))
@no_type_check
def _discard(q: qubit @ owned) -> None: ...


@guppy
@no_type_check
def _discard_array(qubits: array[qubit, N] @ owned) -> None:
    for q in qubits:
        _discard(q)


@guppy.overload(_discard, _discard_array)
@no_type_check
def discard(q) -> None:
    """Discard a single qubit or an array of qubits."""


@hugr_op(quantum_op("MeasureFree"))
@no_type_check
def _measure(q: qubit @ owned) -> bool: ...


@guppy
@no_type_check
def _measure_array(qubits: array[qubit, N] @ owned) -> array[bool, N]:
    return array(_measure(q) for q in qubits)


@guppy.overload(_measure, _measure_array)
@no_type_check
def measure(q):
    """Measure a single qubit or an array of qubits destructively."""


@hugr_op(quantum_op("Reset"))
@no_type_check
def _reset(q: qubit) -> None: ...


@guppy
@no_type_check
def _reset_array(qs: array[qubit, N]) -> None:
    for i in range(N):
        _reset(qs[i])


@guppy.overload(_reset, _reset_array)
@no_type_check
def reset(q) -> None:
    """Reset a single qubit or an array of qubits to the :math:`|0\\rangle` state."""


# Backward-compatible aliases
measure_array = _measure_array
discard_array = _discard_array
reset_array = _reset_array


# -------NON-PRIMITIVE-------


@guppy
@no_type_check
def ch(control: qubit, target: qubit) -> None:
    r"""Controlled-H gate command.

    ch(control, target)

    Qubit ordering: [control, target]

    .. math::
        \mathrm{CH} = \frac{1}{\sqrt{2}}
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 1 & 1 \\
            0 & 0 & 1 & -1
        \end{pmatrix}
    """
    # based on https://quantumcomputing.stackexchange.com/a/15737
    ry(target, -pi / 4)
    cz(control, target)
    ry(target, pi / 4)
