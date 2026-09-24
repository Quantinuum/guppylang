"""Double-precision math operations backed by HUGR's arithmetic.math extension.

Trigonometric functions consume or return floats in radians. Domain and non-finite
results follow the underlying HUGR operations rather than raising Python math
exceptions.
"""

# mypy: disable-error-code="empty-body"

from guppylang_internals.decorator import hugr_op
from guppylang_internals.std._internal.util import float_op
from guppylang_internals.tys.ty import UnitaryFlags
from hugr.std._util import _load_extension

_MATH_EXTENSION = _load_extension("arithmetic.math")

__all__ = [
    "acos",
    "asin",
    "atan",
    "atan2",
    "cos",
    "exp",
    "exp2",
    "fmod",
    "log",
    "log2",
    "log10",
    "pow",
    "sin",
    "tan",
]


@hugr_op(float_op("sin", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def sin(x: float) -> float:
    """Return the sine of x, measured in radians."""


@hugr_op(float_op("cos", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def cos(x: float) -> float:
    """Return the cosine of x, measured in radians."""


@hugr_op(float_op("tan", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def tan(x: float) -> float:
    """Return the tangent of x, measured in radians."""


@hugr_op(float_op("atan", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def atan(x: float) -> float:
    """Return the inverse tangent of x in radians."""


@hugr_op(float_op("atan2", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def atan2(y: float, x: float) -> float:
    r"""Return the four-quadrant inverse tangent of (y, x) in radians.

    For finite inputs with :math:`y \ne 0`, the mathematical definition is:

    .. math::

        \operatorname{atan2}(y, x) =
        \begin{cases}
            \arctan(y/x) & x > 0, \\[5mu]
            \arctan(y/x) + \pi & x < 0 \text{ and } y > 0, \\[5mu]
            \arctan(y/x) - \pi & x < 0 \text{ and } y < 0, \\[5mu]
            +\pi/2 & x = 0 \text{ and } y > 0, \\[5mu]
            -\pi/2 & x = 0 \text{ and } y < 0.
        \end{cases}

    Signed-zero inputs follow the floating-point conventions:

    .. math::

        \operatorname{atan2}(\pm 0, x) =
        \begin{cases}
            \pm 0 & x > 0 \text{ or } x \text{ is } +0, \\[5mu]
            \pm \pi & x < 0 \text{ or } x \text{ is } -0.
        \end{cases}

    The sign of the result matches the sign of :math:`y` in these zero cases.
    The equations describe the mathematical result, not an evaluation of
    :math:`y/x` followed by :func:`atan`, which could overflow or underflow.
    """


@hugr_op(float_op("asin", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def asin(x: float) -> float:
    """Return the inverse sine of x in radians."""


@hugr_op(float_op("acos", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def acos(x: float) -> float:
    """Return the inverse cosine of x in radians."""


@hugr_op(float_op("exp", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def exp(x: float) -> float:
    """Return e raised to the power x."""


@hugr_op(float_op("exp2", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def exp2(x: float) -> float:
    """Return 2 raised to the power x."""


@hugr_op(float_op("log", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def log(x: float) -> float:
    """Return the natural logarithm of x."""


@hugr_op(float_op("log2", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def log2(x: float) -> float:
    """Return the base-two logarithm of x."""


@hugr_op(float_op("log10", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def log10(x: float) -> float:
    """Return the base-ten logarithm of x."""


@hugr_op(float_op("pow", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def pow(x: float, y: float) -> float:
    """Return x raised to the power y."""


@hugr_op(float_op("fmod", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def fmod(x: float, y: float) -> float:
    """Return x - trunc(x / y) * y, with the sign of x."""
