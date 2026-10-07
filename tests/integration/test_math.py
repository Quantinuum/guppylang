import math as pymath
import sys

import pytest
from hugr import ops
from hugr.std.float import FLOAT_T

from guppylang import guppy
from guppylang.std import math
from guppylang.std.angles import angle


@pytest.mark.parametrize(
    "name",
    [
        "sin",
        "cos",
        "tan",
        "atan",
        "asin",
        "acos",
        "exp",
        "exp2",
        "log",
        "log2",
        "log10",
    ],
)
def test_unary_math(name, validate):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> float:
        return fn(x)

    compiled = main.compile_function()
    validate(compiled)
    math_ops = [
        data.op
        for _, data in compiled.modules[0].nodes()
        if isinstance(data.op, ops.ExtOp)
        and data.op.op_def().qualified_name() == f"arithmetic.math.{name}"
    ]
    assert len(math_ops) == 1
    assert math_ops[0].outer_signature().input == [FLOAT_T]
    assert math_ops[0].outer_signature().output == [FLOAT_T]


@pytest.mark.parametrize("name", ["atan2", "pow", "fmod"])
def test_binary_math(name, validate):
    fn = getattr(math, name)

    @guppy
    def main(x: float, y: float) -> float:
        return fn(x, y)

    compiled = main.compile_function()
    validate(compiled)
    math_ops = [
        data.op
        for _, data in compiled.modules[0].nodes()
        if isinstance(data.op, ops.ExtOp)
        and data.op.op_def().qualified_name() == f"arithmetic.math.{name}"
    ]
    assert len(math_ops) == 1
    assert math_ops[0].outer_signature().input == [FLOAT_T, FLOAT_T]
    assert math_ops[0].outer_signature().output == [FLOAT_T]


def test_module_qualified_math(validate):
    @guppy
    def main(x: float, y: float) -> float:
        return math.sin(x) + math.atan2(y, x) + math.fmod(x, y)

    validate(main.compile_function())


def test_sin(run_float_fn_approx) -> None:
    @guppy
    def sin_test() -> float:
        return math.sin(1.5707963267948966)

    run_float_fn_approx(sin_test, 1.0)


@pytest.mark.parametrize("name", ["sin", "cos", "tan"])
# Cases motivated by Go's math implementation and special-case documentation:
# https://go.dev/src/math/sin.go
# https://go.dev/src/math/tan.go
# https://go.dev/src/math/trig_reduce.go
# Compare against the actual rounded radian input, not exact multiples of pi.
@pytest.mark.parametrize(
    "radians",
    [
        -2.0 * pymath.pi,
        -1.5 * pymath.pi,
        -1.0 * pymath.pi,
        -0.75 * pymath.pi,
        -0.5 * pymath.pi,
        -0.25 * pymath.pi,
        -0.0,
        0.0,
        0.25 * pymath.pi,
        0.5 * pymath.pi,
        0.75 * pymath.pi,
        1.0 * pymath.pi,
        1.5 * pymath.pi,
        2.0 * pymath.pi,
        pymath.nextafter(pymath.pi / 2.0, 0.0),
        pymath.nextafter(pymath.pi / 2.0, 2.0),
        -1e-20,
        1e-20,
        -sys.float_info.min,
        sys.float_info.min,
        -pymath.ulp(0.0),
        pymath.ulp(0.0),
        -1e20,
        1e20,
        1e100,
    ],
)
def test_trig_emulation(name, radians, run_float_fn_approx):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> float:
        return fn(x)

    expected = getattr(pymath, name)(radians)
    run_float_fn_approx(main, expected, args=[radians], rel=2e-14, abs=pymath.ulp(0.0))


@pytest.mark.parametrize("name", ["asin", "acos", "atan"])
# https://go.dev/src/math/asin.go: endpoints and values just inside the domain.
@pytest.mark.parametrize(
    "x",
    [
        -1.0,
        pymath.nextafter(-1.0, 0.0),
        -0.7,
        -0.5,
        -1e-20,
        -0.0,
        0.0,
        1e-20,
        0.5,
        0.7,
        pymath.nextafter(1.0, 0.0),
        1.0,
    ],
)
def test_inverse_trig_emulation(name, x, run_float_fn_approx):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> float:
        return fn(x)

    expected = getattr(pymath, name)(x)
    run_float_fn_approx(main, expected, args=[x], rel=2e-14, abs=pymath.ulp(0.0))


# https://go.dev/src/math/atan2.go: quadrants, axes and signed-zero inputs.
@pytest.mark.parametrize("y", [-2.0, -0.0, 0.0, 2.0])
@pytest.mark.parametrize("x", [-1.0, -0.0, 0.0, 1.0])
def test_atan2_emulation(y, x, run_float_fn_approx):
    @guppy
    def main(y: float, x: float) -> float:
        return math.atan2(y, x)

    run_float_fn_approx(
        main,
        pymath.atan2(y, x),
        args=[y, x],
        rel=2e-14,
        abs=pymath.ulp(0.0),
    )


@pytest.mark.parametrize(
    ("name", "x"),
    [("exp", 1.0), ("exp2", 3.0), ("log", 2.0), ("log2", 8.0), ("log10", 100.0)],
)
def test_unary_math_emulation(name, x, run_float_fn_approx):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> float:
        return fn(x)

    run_float_fn_approx(main, getattr(pymath, name)(x), args=[x])


@pytest.mark.parametrize(
    ("name", "x", "y"),
    [("pow", 2.0, 3.0), ("fmod", -7.0, 2.0), ("fmod", 7.0, -2.0)],
)
def test_binary_math_emulation(name, x, y, run_float_fn_approx):
    fn = getattr(math, name)

    @guppy
    def main(x: float, y: float) -> float:
        return fn(x, y)

    run_float_fn_approx(main, getattr(pymath, name)(x, y), args=[x, y])


# https://go.dev/src/math/atan.go: range reduction and large finite inputs.
@pytest.mark.parametrize(
    "x",
    [
        -sys.float_info.max,
        -2.5,
        -1.5,
        -0.66,
        0.66,
        1.5,
        2.5,
        sys.float_info.max,
    ],
)
def test_atan_range(x, run_float_fn_approx):
    @guppy
    def main(x: float) -> float:
        return math.atan(x)

    run_float_fn_approx(main, pymath.atan(x), args=[x], rel=2e-14)


@pytest.mark.parametrize("name", ["sin", "cos", "tan"])
@pytest.mark.parametrize("halfturns", [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0])
def test_trig_angle_emulation(name, halfturns, run_float_fn_approx):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> float:
        return fn(angle(x))

    expected = getattr(pymath, name)(halfturns * pymath.pi)
    run_float_fn_approx(
        main, expected, args=[halfturns], rel=2e-14, abs=pymath.ulp(0.0)
    )


@pytest.mark.parametrize("halfturns", [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0])
def test_angle_trig_methods(halfturns, run_float_fn_approx):
    @guppy
    def main(x: float) -> float:
        return angle(x).sin() ** 2 + angle(x).cos() ** 2

    run_float_fn_approx(main, 1.0, args=[halfturns], rel=2e-14)


@pytest.mark.parametrize("name", ["asin", "acos", "atan"])
@pytest.mark.parametrize("x", [-1.0, -0.5, 0.0, 0.5, 1.0])
def test_inverse_trig_angle_emulation(name, x, run_float_fn_approx):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> float:
        result: angle = fn(x)
        return result.halfturns

    expected = getattr(pymath, name)(x) / pymath.pi
    run_float_fn_approx(main, expected, args=[x], rel=2e-14, abs=pymath.ulp(0.0))


@pytest.mark.parametrize("y", [-2.0, -0.0, 0.0, 2.0])
@pytest.mark.parametrize("x", [-1.0, -0.0, 0.0, 1.0])
def test_atan2_angle_emulation(y, x, run_float_fn_approx):
    @guppy
    def main(y: float, x: float) -> float:
        result: angle = math.atan2(y, x)
        return result.halfturns

    run_float_fn_approx(
        main,
        pymath.atan2(y, x) / pymath.pi,
        args=[y, x],
        rel=2e-14,
        abs=pymath.ulp(0.0),
    )


@pytest.mark.parametrize("name", ["asin", "acos", "atan"])
def test_inverse_trig_angle_return(name, validate):
    fn = getattr(math, name)

    @guppy
    def main(x: float) -> angle:
        return fn(x)

    validate(main.compile_function())


def test_atan2_angle_return(validate):
    @guppy
    def main(y: float, x: float) -> angle:
        return math.atan2(y, x)

    validate(main.compile_function())
