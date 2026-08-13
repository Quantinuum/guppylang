"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="arg-type, empty-body, misc, untyped-decorator, valid-type"

from typing import Self, no_type_check

from guppylang_internals.decorator import custom_function, custom_type, hugr_op
from guppylang_internals.std._internal.compiler.quantum import (
    RotationCompiler,
)
from guppylang_internals.std._internal.compiler.tket_exts import MEASUREMENT_EXTENSION
from guppylang_internals.std._internal.util import quantum_op
from guppylang_internals.tys import Effect
from guppylang_internals.tys.ty import UnitaryFlags
from hugr import tys as ht

from guppylang import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.mem import with_owned
from guppylang.std.option import Option


@guppy.protocol
class AbstractQubit:
    """Abstract interface implemented by qubits accepted by quantum operations."""

    @guppy.require(unitary=True)
    def hadamard(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def controlled_z(self: Self, target: Self) -> None: ...

    @guppy.require(unitary=True)
    def controlled_y(self: Self, target: Self) -> None: ...

    @guppy.require(unitary=True)
    def controlled_x(self: Self, target: Self) -> None: ...

    @guppy.require(unitary=True)
    def phase_t(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def phase_s(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def sqrt_x(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def pauli_x(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def pauli_y(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def pauli_z(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def phase_t_dagger(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def phase_s_dagger(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def sqrt_x_dagger(self: Self) -> None: ...

    @guppy.require(unitary=True)
    def rotate_z(self: Self, theta: angle) -> None: ...

    @guppy.require(unitary=True)
    def rotate_x(self: Self, theta: angle) -> None: ...

    @guppy.require(unitary=True)
    def rotate_y(self: Self, theta: angle) -> None: ...

    @guppy.require(unitary=True)
    def controlled_rotate_z(self: Self, target: Self, theta: angle) -> None: ...

    @guppy.require(unitary=True)
    def toffoli(self: Self, control2: Self, target: Self) -> None: ...

    @guppy.require(unitary=True)
    def controlled_hadamard(self: Self, target: Self) -> None: ...

    @guppy.require
    def measure(self: Self @ owned) -> "Measurement": ...

    @guppy.require
    def project_z(self: Self) -> "Measurement": ...

    @guppy.require
    def discard(self: Self @ owned) -> None: ...

    @guppy.require
    def reset(self: Self) -> None: ...


@custom_type(ht.Qubit, copyable=False, droppable=False)
class qubit:
    @hugr_op(quantum_op("QAlloc"), effects=[Effect.ANY])
    @no_type_check
    def __new__() -> "qubit": ...

    @guppy(unitary=True)
    @no_type_check
    def hadamard(self: "qubit") -> None:
        _h(self)

    @guppy(unitary=True)
    @no_type_check
    def controlled_z(self: "qubit", target: "qubit") -> None:
        _cz(self, target)

    @guppy(unitary=True)
    @no_type_check
    def controlled_y(self: "qubit", target: "qubit") -> None:
        _cy(self, target)

    @guppy(unitary=True)
    @no_type_check
    def controlled_x(self: "qubit", target: "qubit") -> None:
        _cx(self, target)

    @guppy(unitary=True)
    @no_type_check
    def phase_t(self: "qubit") -> None:
        _t(self)

    @guppy(unitary=True)
    @no_type_check
    def phase_s(self: "qubit") -> None:
        _s(self)

    @guppy(unitary=True)
    @no_type_check
    def sqrt_x(self: "qubit") -> None:
        _v(self)

    @guppy(unitary=True)
    @no_type_check
    def pauli_x(self: "qubit") -> None:
        _x(self)

    @guppy(unitary=True)
    @no_type_check
    def pauli_y(self: "qubit") -> None:
        _y(self)

    @guppy(unitary=True)
    @no_type_check
    def pauli_z(self: "qubit") -> None:
        _z(self)

    @guppy(unitary=True)
    @no_type_check
    def phase_t_dagger(self: "qubit") -> None:
        _tdg(self)

    @guppy(unitary=True)
    @no_type_check
    def phase_s_dagger(self: "qubit") -> None:
        _sdg(self)

    @guppy(unitary=True)
    @no_type_check
    def sqrt_x_dagger(self: "qubit") -> None:
        _vdg(self)

    @guppy(unitary=True)
    @no_type_check
    def rotate_z(self: "qubit", theta: angle) -> None:
        _rz(self, theta)

    @guppy(unitary=True)
    @no_type_check
    def rotate_x(self: "qubit", theta: angle) -> None:
        _rx(self, theta)

    @guppy(unitary=True)
    @no_type_check
    def rotate_y(self: "qubit", theta: angle) -> None:
        _ry(self, theta)

    @guppy(unitary=True)
    @no_type_check
    def controlled_rotate_z(self: "qubit", target: "qubit", theta: angle) -> None:
        _crz(self, target, theta)

    @guppy(unitary=True)
    @no_type_check
    def toffoli(self: "qubit", control2: "qubit", target: "qubit") -> None:
        _toffoli(self, control2, target)

    @guppy(unitary=True)
    @no_type_check
    def controlled_hadamard(self: "qubit", target: "qubit") -> None:
        _ch(self, target)

    @guppy
    @no_type_check
    def measure(self: "qubit" @ owned) -> "Measurement":
        return _measure(self)

    @guppy
    @no_type_check
    def project_z(self: "qubit") -> "Measurement":
        return _project_z(self)

    @guppy
    @no_type_check
    def discard(self: "qubit" @ owned) -> None:
        _discard(self)

    @guppy
    @no_type_check
    def reset(self: "qubit") -> None:
        _reset(self)


@custom_type(
    ht.ExtType(MEASUREMENT_EXTENSION.get_type("Measurement")),
    copyable=True,
    droppable=True,
)
class Measurement:
    """Represents the result of a lazy measurement which needs to be explicitly read
    before being used."""

    @hugr_op(quantum_op("Read", MEASUREMENT_EXTENSION))
    @no_type_check
    def read(self: "Measurement") -> bool:
        """Read the measurement result, obtaining a bool. Blocks until the result is
        available if the measurement hasn't been performed yet since being requested.
        """

    @guppy
    @no_type_check
    def __bool__(self: "Measurement") -> bool:
        return self.read()


@hugr_op(quantum_op("TryQAlloc"))
@no_type_check
def maybe_qubit() -> Option[qubit]:
    """Try to allocate a qubit, returning `some(qubit)`
    if allocation succeeds or `nothing` if it fails."""


@hugr_op(quantum_op("H"), unitary_flags=UnitaryFlags.Unitary)
@no_type_check
def _h(q: qubit) -> None:
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
def _cz(control: qubit, target: qubit) -> None:
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
def _cy(control: qubit, target: qubit) -> None:
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
def _cx(control: qubit, target: qubit) -> None:
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
def _t(q: qubit) -> None:
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
def _s(q: qubit) -> None:
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
def _v(q: qubit) -> None:
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
def _x(q: qubit) -> None:
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
def _y(q: qubit) -> None:
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
def _z(q: qubit) -> None:
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
def _tdg(q: qubit) -> None:
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
def _sdg(q: qubit) -> None:
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
def _vdg(q: qubit) -> None:
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
def _rz(q: qubit, angle: angle) -> None:
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
def _rx(q: qubit, angle: angle) -> None:
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
def _ry(q: qubit, angle: angle) -> None:
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
def _crz(control: qubit, target: qubit, angle: angle) -> None:
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
def _toffoli(control1: qubit, control2: qubit, target: qubit) -> None:
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


@guppy
@no_type_check
def _project_z(q: qubit) -> Measurement:
    """Project a single qubit into the Z-basis (a non-destructive measurement)."""

    # TODO revert to using "tket.quantum.Measure" op with InOutMeasureCompiler
    # once bool -> Measurement is available https://github.com/Quantinuum/tket2/issues/1732
    def helper(q: qubit @ owned) -> tuple[Measurement, qubit]:
        return _measure(q), qubit()

    m = with_owned(q, helper)
    if m:
        _x(q)
    return m


@hugr_op(quantum_op("QFree"), effects=[Effect.ANY])
@no_type_check
def _discard(q: qubit @ owned) -> None:
    """Discard a single qubit."""


@hugr_op(quantum_op("MeasureFree"), effects=[Effect.ANY])
@no_type_check
def _measure(q: qubit @ owned) -> Measurement:
    """Request a destructive lazy measurement of a qubit, returning a `Measurement`
    value. Call `.read()` on the value to block until the result is available.
    """


@hugr_op(quantum_op("Reset"))
@no_type_check
def _reset(q: qubit) -> None:
    """Reset a single qubit to the :math:`|0\\rangle` state."""


N = guppy.nat_var("N")


@guppy
@no_type_check
def collect_measurements(
    measurements: array[Measurement, N] @ owned,
) -> array[bool, N]:
    """Block on each measurement until it is available and collect results into an
    array of bools.
    """
    return array(m.read() for m in measurements)


# -------NON-PRIMITIVE-------


@guppy(unitary=True)
@no_type_check
def _ch(control: qubit, target: qubit) -> None:
    r"""Controlled-H gate command.

    ch(control, target)

    Qubit ordering: [control, target]

    .. math::
        \mathrm{CH} =
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 &  \frac{1}{\sqrt{2}} &  \frac{1}{\sqrt{2}} \\
            0 & 0 &  \frac{1}{\sqrt{2}} & -\frac{1}{\sqrt{2}}
        \end{pmatrix}
    """
    # based on https://quantumcomputing.stackexchange.com/a/15737
    _ry(target, -pi / 4)
    _cz(control, target)
    _ry(target, pi / 4)


@guppy(unitary=True)
@no_type_check
def h[Q: AbstractQubit](q: Q) -> None:
    """Apply a Hadamard gate."""
    q.hadamard()


@guppy(unitary=True)
@no_type_check
def cz[Q: AbstractQubit](control: Q, target: Q) -> None:
    """Apply a controlled-Z gate."""
    control.controlled_z(target)


@guppy(unitary=True)
@no_type_check
def cy[Q: AbstractQubit](control: Q, target: Q) -> None:
    """Apply a controlled-Y gate."""
    control.controlled_y(target)


@guppy(unitary=True)
@no_type_check
def cx[Q: AbstractQubit](control: Q, target: Q) -> None:
    """Apply a controlled-X gate."""
    control.controlled_x(target)


@guppy(unitary=True)
@no_type_check
def t[Q: AbstractQubit](q: Q) -> None:
    """Apply a T gate."""
    q.phase_t()


@guppy(unitary=True)
@no_type_check
def s[Q: AbstractQubit](q: Q) -> None:
    """Apply an S gate."""
    q.phase_s()


@guppy(unitary=True)
@no_type_check
def v[Q: AbstractQubit](q: Q) -> None:
    """Apply a V gate."""
    q.sqrt_x()


@guppy(unitary=True)
@no_type_check
def x[Q: AbstractQubit](q: Q) -> None:
    """Apply a Pauli-X gate."""
    q.pauli_x()


@guppy(unitary=True)
@no_type_check
def y[Q: AbstractQubit](q: Q) -> None:
    """Apply a Pauli-Y gate."""
    q.pauli_y()


@guppy(unitary=True)
@no_type_check
def z[Q: AbstractQubit](q: Q) -> None:
    """Apply a Pauli-Z gate."""
    q.pauli_z()


@guppy(unitary=True)
@no_type_check
def tdg[Q: AbstractQubit](q: Q) -> None:
    """Apply a T-dagger gate."""
    q.phase_t_dagger()


@guppy(unitary=True)
@no_type_check
def sdg[Q: AbstractQubit](q: Q) -> None:
    """Apply an S-dagger gate."""
    q.phase_s_dagger()


@guppy(unitary=True)
@no_type_check
def vdg[Q: AbstractQubit](q: Q) -> None:
    """Apply a V-dagger gate."""
    q.sqrt_x_dagger()


@guppy(unitary=True)
@no_type_check
def rz[Q: AbstractQubit](q: Q, theta: angle) -> None:
    """Apply an Rz rotation."""
    q.rotate_z(theta)


@guppy(unitary=True)
@no_type_check
def rx[Q: AbstractQubit](q: Q, theta: angle) -> None:
    """Apply an Rx rotation."""
    q.rotate_x(theta)


@guppy(unitary=True)
@no_type_check
def ry[Q: AbstractQubit](q: Q, theta: angle) -> None:
    """Apply an Ry rotation."""
    q.rotate_y(theta)


@guppy(unitary=True)
@no_type_check
def crz[Q: AbstractQubit](control: Q, target: Q, theta: angle) -> None:
    """Apply a controlled-Rz rotation."""
    control.controlled_rotate_z(target, theta)


@guppy(unitary=True)
@no_type_check
def toffoli[Q: AbstractQubit](control1: Q, control2: Q, target: Q) -> None:
    """Apply a Toffoli gate."""
    control1.toffoli(control2, target)


@guppy
@no_type_check
def project_z[Q: AbstractQubit](q: Q) -> Measurement:
    """Project a qubit into the Z basis without consuming it."""
    return q.project_z()


@guppy
@no_type_check
def discard[Q: AbstractQubit](q: Q @ owned) -> None:
    """Discard a qubit."""
    q.discard()


@guppy
@no_type_check
def measure[Q: AbstractQubit](q: Q @ owned) -> Measurement:
    """Request a destructive lazy measurement of a qubit."""
    return q.measure()


@guppy
@no_type_check
def reset[Q: AbstractQubit](q: Q) -> None:
    """Reset a qubit to the |0> state."""
    q.reset()


@guppy
@no_type_check
def measure_array[Q: AbstractQubit](
    qubits: array[Q, N] @ owned,
) -> array[Measurement, N]:
    """Request destructive lazy measurements of an array of qubits."""
    return array(measure(q) for q in qubits)


@guppy
@no_type_check
def discard_array[Q: AbstractQubit](qubits: array[Q, N] @ owned) -> None:
    """Discard an array of qubits."""
    for i in range(N):
        if not qubits.is_borrowed(i):
            discard(qubits.take(i))
    qubits.discard_all_taken()


@guppy(unitary=True)
@no_type_check
def ch[Q: AbstractQubit](control: Q, target: Q) -> None:
    """Apply a controlled-Hadamard gate."""
    control.controlled_hadamard(target)
