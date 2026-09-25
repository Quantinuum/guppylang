"""Double-precision math operations backed by HUGR's arithmetic.math extension.

Trigonometric functions support floats in radians and Guppy angles. Inverse
trigonometric functions return floats unless an angle result is required by the
surrounding type context. Domain and non-finite results follow the underlying
HUGR operations rather than raising Python math exceptions.
"""

# mypy: disable-error-code="empty-body"

from guppylang_internals.decorator import custom_function, hugr_op
from guppylang_internals.std._internal.compiler.math import TrigCompiler
from guppylang_internals.std._internal.util import float_op
from guppylang_internals.tys.ty import UnitaryFlags
from hugr.std._util import _load_extension

from guppylang.decorator import guppy
from guppylang.std.angles import angle

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
def _sin_float(x: float) -> float: ...


@custom_function(
    TrigCompiler("sin", math_extension=_MATH_EXTENSION, inverse=False),
    unitary_flags=UnitaryFlags.Dagger,
)
def _sin_angle(x: angle) -> float: ...


@guppy.overload(_sin_float, _sin_angle)
def sin(x: float | angle) -> float:
    """Return the sine of a float in radians or a Guppy angle."""


@hugr_op(float_op("cos", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def _cos_float(x: float) -> float: ...


@custom_function(
    TrigCompiler("cos", math_extension=_MATH_EXTENSION, inverse=False),
    unitary_flags=UnitaryFlags.Dagger,
)
def _cos_angle(x: angle) -> float: ...


@guppy.overload(_cos_float, _cos_angle)
def cos(x: float | angle) -> float:
    """Return the cosine of a float in radians or a Guppy angle."""


@hugr_op(float_op("tan", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def _tan_float(x: float) -> float: ...


@custom_function(
    TrigCompiler("tan", math_extension=_MATH_EXTENSION, inverse=False),
    unitary_flags=UnitaryFlags.Dagger,
)
def _tan_angle(x: angle) -> float: ...


@guppy.overload(_tan_float, _tan_angle)
def tan(x: float | angle) -> float:
    """Return the tangent of a float in radians or a Guppy angle."""


@hugr_op(float_op("atan", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def _atan_float(x: float) -> float: ...


@custom_function(
    TrigCompiler("atan", math_extension=_MATH_EXTENSION, inverse=True),
    unitary_flags=UnitaryFlags.Dagger,
)
def _atan_angle(x: float) -> angle: ...


@guppy.overload(_atan_float, _atan_angle)
def atan(x: float) -> float | angle:
    """Return the inverse tangent of x as a float in radians or an angle.

    Returns a float unless the expected return type is ``angle``.
    """


@hugr_op(float_op("atan2", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def _atan2_float(y: float, x: float) -> float: ...


@custom_function(
    TrigCompiler("atan2", math_extension=_MATH_EXTENSION, inverse=True),
    unitary_flags=UnitaryFlags.Dagger,
)
def _atan2_angle(y: float, x: float) -> angle: ...


@guppy.overload(_atan2_float, _atan2_angle)
def atan2(y: float, x: float) -> float | angle:
    r"""Return the four-quadrant inverse tangent of (y, x).

    Returns a float in radians unless the expected return type is ``angle``.
    The equations below express the result in radians.

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
def _asin_float(x: float) -> float: ...


@custom_function(
    TrigCompiler("asin", math_extension=_MATH_EXTENSION, inverse=True),
    unitary_flags=UnitaryFlags.Dagger,
)
def _asin_angle(x: float) -> angle: ...


@guppy.overload(_asin_float, _asin_angle)
def asin(x: float) -> float | angle:
    """Return the inverse sine of x as a float in radians or an angle.

    Returns a float unless the expected return type is ``angle``.
    """


@hugr_op(float_op("acos", _MATH_EXTENSION), unitary_flags=UnitaryFlags.Dagger)
def _acos_float(x: float) -> float: ...


@custom_function(
    TrigCompiler("acos", math_extension=_MATH_EXTENSION, inverse=True),
    unitary_flags=UnitaryFlags.Dagger,
)
def _acos_angle(x: float) -> angle: ...


@guppy.overload(_acos_float, _acos_angle)
def acos(x: float) -> float | angle:
    """Return the inverse cosine of x as a float in radians or an angle.

    Returns a float unless the expected return type is ``angle``.
    """


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
