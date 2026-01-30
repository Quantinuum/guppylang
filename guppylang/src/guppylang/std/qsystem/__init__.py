"""Guppy standard library for Quantinuum systems device operations."""

from typing import no_type_check

from guppylang_internals.decorator import custom_function, hugr_op
from guppylang_internals.definition.custom import BoolOpCompiler
from guppylang_internals.std._internal.compiler.quantum import (
    InoutMeasureCompiler,
    InoutMeasureResetCompiler,
)
from guppylang_internals.std._internal.compiler.tket_exts import QSYSTEM_EXTENSION
from guppylang_internals.std._internal.util import quantum_op

from guppylang import guppy
from guppylang.std import angles
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import owned
from guppylang.std.futures import Future
from guppylang.std.option import Option, nothing, some
from guppylang.std.quantum import qubit


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


@hugr_op(quantum_op("Measure", ext=QSYSTEM_EXTENSION))
@no_type_check
def measure(q: qubit @ owned) -> bool:
    """Measure a qubit destructively."""


@custom_function(InoutMeasureResetCompiler("MeasureReset", QSYSTEM_EXTENSION))
@no_type_check
def measure_and_reset(q: qubit) -> bool:
    """MeasureReset operation from the qsystem extension."""


@hugr_op(quantum_op("Reset", ext=QSYSTEM_EXTENSION))
@no_type_check
def reset(q: qubit) -> None:
    """Reset a qubit to the :math:`|0\\rangle` state."""


# TODO
# @hugr_op(quantum_op("TryQAlloc", ext=QSYSTEM_EXTENSION))
# @no_type_check
# def _try_qalloc() -> Option[qubit]:
#     ..


@hugr_op(quantum_op("QFree", ext=QSYSTEM_EXTENSION))
@no_type_check
def qfree(q: qubit @ owned) -> None: ...


@hugr_op(quantum_op("LazyMeasureLeaked", ext=QSYSTEM_EXTENSION))
@no_type_check
def _measure_leaked(q: qubit @ owned) -> Future[int]:
    """Measure the quibit or return 2 if it is leaked."""


@guppy
@no_type_check
def measure_leaked(q: qubit @ owned) -> "MaybeLeaked":
    """Measure the qubit and return a MaybeLeaked result."""
    fm = _measure_leaked(q)
    return MaybeLeaked(fm)


@guppy.struct
@no_type_check
class MaybeLeaked:
    """A class representing a measurement that may have leaked.

    This is used to represent the result of `measure_leaked`, which can either
    return a boolean measurement result or indicate that the qubit has leaked.
    """

    _measurement: Future[int]  # type: ignore[type-arg]

    @guppy
    @no_type_check
    def is_leaked(self: "MaybeLeaked") -> bool:
        """Check if the measurement indicates a leak."""
        return self._measurement.copy().read() == 2

    @guppy
    @no_type_check
    def to_result(self: "MaybeLeaked @ owned") -> Option[bool]:
        """Returns the measurement result or `nothing` if leaked."""
        int_value: int = self._measurement.read()
        if int_value == 2:
            return nothing()
        measurement = int_value == 1
        return some(measurement)

    @guppy
    @no_type_check
    def discard(self: "MaybeLeaked @ owned") -> None:
        self._measurement.discard()


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@hugr_op(quantum_op("PhasedX", ext=QSYSTEM_EXTENSION))
@no_type_check
def _phased_x(q: qubit, angle1: float, angle2: float) -> None:
    """PhasedX operation from the qsystem extension.

    See ``guppylang.std.qsystem.phased_x`` for a public definition that
    accepts angle parameters.
    """


@hugr_op(quantum_op("ZZPhase", ext=QSYSTEM_EXTENSION))
@no_type_check
def _zz_phase(q1: qubit, q2: qubit, angle: float) -> None:
    """ZZPhase operation from the qsystem extension.

    See ``guppylang.std.qsystem.zz_phase`` for a public definition that
    accepts angle parameters.
    """


@hugr_op(quantum_op("Rz", ext=QSYSTEM_EXTENSION))
@no_type_check
def _rz(q: qubit, angle: float) -> None:
    """Rz operation from the qsystem extension.

    See ``guppylang.std.qsystem.rz`` for a public definition that
    accepts angle parameters.
    """
