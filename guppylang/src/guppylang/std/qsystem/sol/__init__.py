"""Guppy standard library for Quantinuum Sol system operations."""

from typing import no_type_check

from guppylang_internals.decorator import custom_function, hugr_op
from guppylang_internals.std._internal.compiler.qsystem import (
    LazyMeasureResetCompiler,
)
from guppylang_internals.std._internal.compiler.quantum import (
    InoutMeasureResetCompiler,
)
from guppylang_internals.std._internal.compiler.tket_exts import (
    QSYSTEM_SOL_EXTENSION,
)
from guppylang_internals.std._internal.util import quantum_op

from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.builtins import owned
from guppylang.std.futures import Future
from guppylang.std.qsystem._common import (
    MaybeLeaked,
    Measurement,
    collect_measurements,
)
from guppylang.std.quantum import qubit

__all__ = [
    "MaybeLeaked",
    "Measurement",
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
    "phased_xx",
    "qfree",
    "reset",
    "rz",
]

N = guppy.nat_var("N")


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
def phased_xx(q1: qubit, q2: qubit, angle1: angle, angle2: angle) -> None:
    r"""phased_xx gate command. The native 2-qubit entangling gate on Sol.

    .. math::

        \mathrm{PhasedXX}(\theta_1, \theta_2) =
        \exp\!\Bigl(-\tfrac{i\theta_1}{2}
          \bigl(\cos\theta_2 \,(X{\otimes}X - Y{\otimes}Y) +
                \sin\theta_2 \,(X{\otimes}Y + Y{\otimes}X)\bigr)\Bigr)
    """
    f1 = float(angle1)
    f2 = float(angle2)
    _phased_xx(q1, q2, f1, f2)


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


@hugr_op(quantum_op("Measure", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def measure(q: qubit @ owned) -> bool:
    """Measure a qubit destructively."""


@hugr_op(quantum_op("Reset", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def reset(q: qubit) -> None:
    """Reset a qubit to the :math:`|0\\rangle` state."""


@hugr_op(quantum_op("QFree", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def qfree(q: qubit @ owned) -> None: ...


@hugr_op(quantum_op("LazyMeasureLeaked", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def _measure_leaked(q: qubit @ owned) -> Future[int]:
    """Measure the qubit or return 2 if it is leaked."""


@guppy
@no_type_check
def measure_leaked(q: qubit @ owned) -> MaybeLeaked:
    """Measure the qubit and return a MaybeLeaked result."""
    fm = _measure_leaked(q)
    return MaybeLeaked(fm)


@hugr_op(quantum_op("LazyMeasure", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def lazy_measure(q: qubit @ owned) -> Measurement:
    """Request a destructive lazy measurement of a qubit, returning a ``Measurement``
    value. Call ``.read()`` on the value to block until the result is available.
    """


@custom_function(compiler=LazyMeasureResetCompiler(QSYSTEM_SOL_EXTENSION))
@no_type_check
def lazy_measure_and_reset(q: qubit) -> Measurement:
    """Like ``lazy_measure``, but also resets the qubit after measurement."""


@custom_function(InoutMeasureResetCompiler("MeasureReset", QSYSTEM_SOL_EXTENSION))
@no_type_check
def measure_and_reset(q: qubit) -> bool:
    """MeasureReset operation from the qsystem extension."""


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[bool, N]:
    """Measure an array of qubits, returning an array of bools."""
    return array(measure(q) for q in qubits)


@guppy
@no_type_check
def measure_and_reset_array(qubits: array[qubit, N]) -> array[bool, N]:
    """Measure and reset an array of qubits, returning an array of bools."""
    return array(measure_and_reset(qubits[i]) for i in range(N))


@guppy
@no_type_check
def lazy_measure_array(qubits: array[qubit, N] @ owned) -> array[Measurement, N]:
    """Request a destructive lazy measurement of an array of qubits, returning an array
    of ``Measurement`` values. Call ``.read()`` on each value to block until results are
    available.
    """
    return array(lazy_measure(q) for q in qubits)


@guppy
@no_type_check
def lazy_measure_and_reset_array(
    qubits: array[qubit, N],
) -> array[Measurement, N]:
    """Like ``lazy_measure_array``, but also resets each qubit after measurement."""
    return array(lazy_measure_and_reset(qubits[i]) for i in range(N))


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@hugr_op(quantum_op("PhasedX", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def _phased_x(q: qubit, angle1: float, angle2: float) -> None:
    """PhasedX operation from the qsystem sol extension.

    See ``guppylang.std.qsystem.sol.phased_x`` for a public definition that
    accepts angle parameters.
    """


@hugr_op(quantum_op("PhasedXX", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def _phased_xx(q1: qubit, q2: qubit, angle1: float, angle2: float) -> None:
    """PhasedXX operation from the qsystem sol extension.

    See ``guppylang.std.qsystem.sol.phased_xx`` for a public definition that
    accepts angle parameters.
    """


@hugr_op(quantum_op("Rz", ext=QSYSTEM_SOL_EXTENSION))
@no_type_check
def _rz(q: qubit, angle: float) -> None:
    """Rz operation from the qsystem sol extension.

    See ``guppylang.std.qsystem.sol.rz`` for a public definition that
    accepts angle parameters.
    """
