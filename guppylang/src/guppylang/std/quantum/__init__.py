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


@hugr_op(quantum_op("H"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def h(q: qubit) -> None:
    r"""Hadamard gate command

    .. math::
        \mathrm{H}= \frac{1}{\sqrt{2}}
          \begin{pmatrix}
            1 & 1 \\
            1 & -1
          \end{pmatrix}
    """


@hugr_op(quantum_op("CZ"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def cz(control: qubit, target: qubit) -> None:
    r"""Controlled-Z gate command.

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
def cy(control: qubit, target: qubit) -> None:
    r"""Controlled-Y gate command.

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
def cx(control: qubit, target: qubit) -> None:
    r"""Controlled-X gate command.

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
def t(q: qubit) -> None:
    r"""T gate.

    .. math::
        \mathrm{T}=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{i \frac{\pi}{4}}
           \end{pmatrix}

    """


@hugr_op(quantum_op("S"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def s(q: qubit) -> None:
    r"""S gate.

    .. math::
        \mathrm{S}=
          \begin{pmatrix}
            1 & 0 \\
            0 & i
           \end{pmatrix}

    """


@hugr_op(quantum_op("V"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def v(q: qubit) -> None:
    r"""V gate.

    .. math::
      \mathrm{V}= \frac{1}{\sqrt{2}}
       \begin{pmatrix}
            1 & -i \\
            -i & 1
           \end{pmatrix}

    """


@hugr_op(quantum_op("X"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def x(q: qubit) -> None:
    r"""X gate.

    .. math::
        \mathrm{X}=
          \begin{pmatrix}
            0 & 1 \\
            1 & 0
           \end{pmatrix}

    """


@hugr_op(quantum_op("Y"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def y(q: qubit) -> None:
    r"""Y gate.

    .. math::
        \mathrm{Y}=
          \begin{pmatrix}
            0 & -i \\
            i & 0
           \end{pmatrix}

    """


@hugr_op(quantum_op("Z"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def z(q: qubit) -> None:
    r"""Z gate.

    .. math::
        \mathrm{Z}=
          \begin{pmatrix}
            1 & 0 \\
            0 & -1
           \end{pmatrix}

    """


@hugr_op(quantum_op("Tdg"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def tdg(q: qubit) -> None:
    r"""Tdg gate.

    .. math::
        \mathrm{T}^\dagger=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{-i \frac{\pi}{4}}
           \end{pmatrix}

    """


@hugr_op(quantum_op("Sdg"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def sdg(q: qubit) -> None:
    r"""Sdg gate.

    .. math::
        \mathrm{S}^\dagger=
          \begin{pmatrix}
            1 & 0 \\
            0 & -i
           \end{pmatrix}

    """


@hugr_op(quantum_op("Vdg"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def vdg(q: qubit) -> None:
    r"""Vdg gate.

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
def discard(q: qubit @ owned) -> None:
    """Discard a single qubit."""


@hugr_op(quantum_op("MeasureFree"))
@no_type_check
def measure(q: qubit @ owned) -> bool:
    """Measure a single qubit destructively."""


@hugr_op(quantum_op("Reset"))
@no_type_check
def reset(q: qubit) -> None:
    """Reset a single qubit to the :math:`|0\rangle` state."""


N = guppy.nat_var("N")


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[bool, N]:
    """Measure an array of qubits, returning an array of bools."""
    return array(measure(q) for q in qubits)


@guppy
@no_type_check
def discard_array(qubits: array[qubit, N] @ owned) -> None:
    """Discard an array of qubits."""
    for q in qubits:
        discard(q)


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
