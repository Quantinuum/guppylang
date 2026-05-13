"""Guppy standard library for Quantinuum Helios system operations."""

from typing import no_type_check

from guppylang_internals.decorator import custom_function, hugr_op
from guppylang_internals.std._internal.compiler.quantum import (
    InoutMeasureCompiler,
)
from guppylang_internals.std._internal.compiler.tket_exts import (
    QSYSTEM_HELIOS_EXTENSION,
)
from guppylang_internals.std._internal.util import quantum_op

from guppylang import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.futures import Future
from guppylang.std.qsystem._common import (
    MaybeLeaked,
    collect_measurements,
)
from guppylang.std.quantum import Measurement, qubit

__all__ = [
    "MaybeLeaked",
    "collect_measurements",
    "lazy_measure",
    "lazy_measure_and_reset",
    "lazy_measure_and_reset_array",
    "lazy_measure_array",
    "measure",
    "measure_and_reset",
    "measure_and_reset_array",
    "measure_array",
    "measure_leaked",
    "phased_x",
    "qfree",
    "reset",
    "rz",
    "zz_max",
    "zz_phase",
]


@guppy
@no_type_check
def phased_x(q: qubit, angle1: angle, angle2: angle) -> None:
    r"""phased_x gate command.

    .. math::

        \mathrm{PhasedX}(\theta_1, \theta_2)=
          \mathrm{Rz(\theta_2)Rx(\theta_1)Rz(-\theta_2)}&=
          \begin{pmatrix}
          \cos(\frac{ \theta_1}{2}) &
            -i e^{-i \theta_2}\sin(\frac{\theta_1}{2})\\
          -i e^{i \theta_2}\sin(\frac{\theta_1}{2}) &
            \cos(\frac{\theta_1}{2})
           \end{pmatrix}
    """
    f1 = float(angle1)
    f2 = float(angle2)
    _phased_x(q, f1, f2)


@guppy
@no_type_check
def zz_max(q1: qubit, q2: qubit) -> None:
    r"""zz_max gate command. A maximally entangling zz_phase gate.

    This is a special case of the zz_phase command with :math:`\theta = \frac{\pi}{2}`.

    zz_max(q1, q2)

    Qubit ordering: [q1, q2]

    .. math::
        \mathrm{ZZMax}=
        \exp(\frac{- i\pi}{4}\big(Z \otimes Z \big))=
          \begin{pmatrix}
            e^{\frac{-i\pi}{4}} & 0 & 0 & 0 \\
            0 & e^{\frac{i\pi}{4}} & 0 & 0 \\
            0 & 0 & e^{\frac{i\pi}{4}} & 0 \\
            0 & 0 & 0 & e^{\frac{-i\pi}{4}}
        \end{pmatrix}
    """
    zz_phase(q1, q2, pi / 2)


@guppy
@no_type_check
def zz_phase(q1: qubit, q2: qubit, angle: angle) -> None:
    r"""zz_phase gate command.

    zz_phase(q1, q2, theta)

    Qubit ordering: [q1, q2]

    .. math::
        \mathrm{ZZPhase}(\theta)=
        \exp(\frac{- i \theta}{2}\big(Z \otimes Z \big))=
          \begin{pmatrix}
            e^{\frac{-i \theta}{2}} & 0 & 0 & 0 \\
            0 & e^{\frac{i \theta}{2}} & 0 & 0 \\
            0 & 0 & e^{\frac{i \theta}{2}} & 0 \\
            0 & 0 & 0 & e^{\frac{-i \theta}{2}}
        \end{pmatrix}

    >>> @guppy
    ... def qsystem_cx(q1: qubit, q2: qubit) -> None:
    ...     phased_x(angle(3/2), angle(-1/2), q2)
    ...     zz_phase(q1, q2, angle(1/2))
    ...     rz(angle(5/2), q1)
    ...     phasedx(angle(-3/2), q1)
    ...     rz(angle(3/2), q2)
    >>> qsystem_cx.compile()
    """
    f = float(angle)
    _zz_phase(q1, q2, f)


@guppy
@no_type_check
def rz(q: qubit, angle: angle) -> None:
    r"""rz gate command.

    .. math::
        \mathrm{Rz}(\theta)=
        \exp(\frac{- i \theta}{2} Z)=
          \begin{pmatrix}
            e^{\frac{-i \theta}{2}} & 0  \\
            0 & e^{\frac{i \theta}{2}}
        \end{pmatrix}
    """

    f1 = float(angle)
    _rz(q, f1)


@guppy
@no_type_check
def measure(q: qubit @ owned) -> Measurement:
    """Request a destructive lazy measurement of a qubit, returning a `Measurement`
    value. Call `.read()` on the value to block until the result is available. This is
    equivalent to `lazy_measure`.
    """
    return lazy_measure(q)


@guppy
@no_type_check
def measure_and_reset(q: qubit) -> Measurement:
    """Like `measure`, but also resets the qubit after measurement. This is
    equivalent to `lazy_measure_and_reset`."""
    return lazy_measure_and_reset(q)


@hugr_op(quantum_op("Reset", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def reset(q: qubit) -> None:
    """Reset a qubit to the :math:`|0\\rangle` state."""


# TODO
# @hugr_op(quantum_op("TryQAlloc", ext=QSYSTEM_HELIOS_EXTENSION))
# @no_type_check
# def _try_qalloc() -> Option[qubit]:
#     ..


@hugr_op(quantum_op("QFree", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def qfree(q: qubit @ owned) -> None: ...


@hugr_op(quantum_op("LazyMeasureLeaked", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def _measure_leaked(q: qubit @ owned) -> Future[int]:
    """Measure the qubit or return 2 if it is leaked."""


@guppy
@no_type_check
def measure_leaked(q: qubit @ owned) -> "MaybeLeaked":
    """Measure the qubit and return a MaybeLeaked result."""
    fm = _measure_leaked(q)
    return MaybeLeaked(fm)


@guppy
@no_type_check
def lazy_measure(q: qubit @ owned) -> Measurement:
    """Request a destructive lazy measurement of a qubit, returning a `Measurement`
    value. Call `.read()` on the value to block until the result is available. This is
    equivalent to `measure`.
    """
    result = _lazy_measure(q)
    return _future_to_measurement(result)


@guppy
@no_type_check
def lazy_measure_and_reset(q: qubit) -> Measurement:
    """Like `lazy_measure`, but also resets the qubit after measurement. This is
    equivalent to `measure_and_reset`."""
    result = _lazy_measure_and_reset(q)
    return _future_to_measurement(result)


# Measurement functions directly mapping onto `tket.qsystem` ops without the conversion
# to measurement (which ensures compatibility with `std.quantum` functions).
@hugr_op(quantum_op("LazyMeasure", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def _lazy_measure(q: qubit @ owned) -> Future[bool]: ...


@custom_function(
    InoutMeasureCompiler(
        "LazyMeasureReset", ext=QSYSTEM_HELIOS_EXTENSION, return_future=True
    )
)
@no_type_check
def _lazy_measure_and_reset(q: qubit) -> Future[bool]: ...


@hugr_op(quantum_op("FutureToMeasurement", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def _future_to_measurement(result: Future[bool] @ owned) -> Measurement: ...


N = guppy.nat_var("N")


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[Measurement, N]:
    """Lazily measure an array of qubits using `measure`, returning an array of
    measurements. Equivalent to `lazy_measure_array`.
    """
    return array(measure(q) for q in qubits)


@guppy
@no_type_check
def measure_and_reset_array(qubits: array[qubit, N]) -> array[Measurement, N]:
    """Lazily measure and reset an array of qubits using `measure_and_reset`,
    returning an array of measurements. Equivalent to `lazy_measure_and_reset_array`.
    """
    return array(measure_and_reset(qubits[i]) for i in range(N))


@guppy
@no_type_check
def lazy_measure_array(
    qubits: array[qubit, N] @ owned,
) -> array["Measurement", N]:
    """Same as `measure_array` as the standard measurement behaviour is already
    lazy.
    """
    return array(lazy_measure(q) for q in qubits)


@guppy
@no_type_check
def lazy_measure_and_reset_array(
    qubits: array[qubit, N],
) -> array["Measurement", N]:
    """Same as `measure_and_reset_array` as the standard measurement behaviour is
    already lazy.
    """
    return array(lazy_measure_and_reset(qubits[i]) for i in range(N))


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@hugr_op(quantum_op("PhasedX", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def _phased_x(q: qubit, angle1: float, angle2: float) -> None:
    """PhasedX operation from the qsystem extension.

    See ``guppylang.std.qsystem.phased_x`` for a public definition that
    accepts angle parameters.
    """


@hugr_op(quantum_op("ZZPhase", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def _zz_phase(q1: qubit, q2: qubit, angle: float) -> None:
    """ZZPhase operation from the qsystem extension.

    See ``guppylang.std.qsystem.zz_phase`` for a public definition that
    accepts angle parameters.
    """


@hugr_op(quantum_op("Rz", ext=QSYSTEM_HELIOS_EXTENSION))
@no_type_check
def _rz(q: qubit, angle: float) -> None:
    """Rz operation from the qsystem extension.

    See ``guppylang.std.qsystem.rz`` for a public definition that
    accepts angle parameters.
    """
