import math as pymath
import sys

from hugr import ops
from hugr.std.float import FLOAT_T

from guppylang import guppy
from guppylang.std import math
from guppylang.std.angles import angle
from guppylang.std.builtins import output


def test_unary_math(validate):
    @guppy
    def main(
        x: float,
    ) -> tuple[
        float, float, float, float, float, float, float, float, float, float, float
    ]:
        return (
            math.sin(x),
            math.cos(x),
            math.tan(x),
            math.atan(x),
            math.asin(x),
            math.acos(x),
            math.exp(x),
            math.exp2(x),
            math.log(x),
            math.log2(x),
            math.log10(x),
        )

    compiled = main.compile_function()
    validate(compiled)
    math_ops = [
        data.op
        for _, data in compiled.modules[0].nodes()
        if isinstance(data.op, ops.ExtOp)
        and data.op.op_def().qualified_name().startswith("arithmetic.math.")
    ]
    assert len(math_ops) == 11
    assert {op.op_def().qualified_name() for op in math_ops} == {
        f"arithmetic.math.{name}"
        for name in [
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
        ]
    }
    for op in math_ops:
        assert op.outer_signature().input == [FLOAT_T]
        assert op.outer_signature().output == [FLOAT_T]


def test_binary_math(validate):
    @guppy
    def main(x: float, y: float) -> tuple[float, float, float]:
        return math.atan2(x, y), math.pow(x, y), math.fmod(x, y)

    compiled = main.compile_function()
    validate(compiled)
    math_ops = [
        data.op
        for _, data in compiled.modules[0].nodes()
        if isinstance(data.op, ops.ExtOp)
        and data.op.op_def().qualified_name().startswith("arithmetic.math.")
    ]
    assert len(math_ops) == 3
    assert {op.op_def().qualified_name() for op in math_ops} == {
        f"arithmetic.math.{name}" for name in ["atan2", "pow", "fmod"]
    }
    for op in math_ops:
        assert op.outer_signature().input == [FLOAT_T, FLOAT_T]
        assert op.outer_signature().output == [FLOAT_T]


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


def test_trig_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float) -> None:
        output("_test_output", math.sin(x))
        output("_test_output", math.cos(x))
        output("_test_output", math.tan(x))

    # Cases motivated by Go's math implementation and special-case documentation:
    # https://go.dev/src/math/sin.go
    # https://go.dev/src/math/tan.go
    # https://go.dev/src/math/trig_reduce.go
    # Compare against the actual rounded radian input, not exact multiples of pi.
    radians = [
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
    ]
    expected = [
        [getattr(pymath, name)(x) for name in ["sin", "cos", "tan"]] for x in radians
    ]
    run_float_fn_approx_per_shot(
        main, expected, args=[{"x": x} for x in radians], rel=2e-14, abs=pymath.ulp(0.0)
    )


def test_inverse_trig_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float) -> None:
        output("_test_output", math.asin(x))
        output("_test_output", math.acos(x))
        output("_test_output", math.atan(x))

    # https://go.dev/src/math/asin.go: endpoints and values just inside the domain.
    xs = [
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
    ]
    expected = [
        [getattr(pymath, name)(x) for name in ["asin", "acos", "atan"]] for x in xs
    ]
    run_float_fn_approx_per_shot(
        main, expected, args=[{"x": x} for x in xs], rel=2e-14, abs=pymath.ulp(0.0)
    )


# https://go.dev/src/math/atan2.go: quadrants, axes and signed-zero inputs.
def test_atan2_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(y: float, x: float) -> None:
        output("_test_output", math.atan2(y, x))

    args = [
        {"y": y, "x": x} for y in [-2.0, -0.0, 0.0, 2.0] for x in [-1.0, -0.0, 0.0, 1.0]
    ]
    run_float_fn_approx_per_shot(
        main,
        [pymath.atan2(shot_args["y"], shot_args["x"]) for shot_args in args],
        args=args,
        rel=2e-14,
        abs=pymath.ulp(0.0),
    )


def test_unary_math_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float) -> None:
        output("_test_output", math.exp(x))
        output("_test_output", math.exp2(x))
        output("_test_output", math.log(x))
        output("_test_output", math.log2(x))
        output("_test_output", math.log10(x))

    xs = [1.0, 3.0, 2.0, 8.0, 100.0]
    expected = [
        [getattr(pymath, name)(x) for name in ["exp", "exp2", "log", "log2", "log10"]]
        for x in xs
    ]
    run_float_fn_approx_per_shot(main, expected, args=[{"x": x} for x in xs])


def test_binary_math_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float, y: float) -> None:
        output("_test_output", math.pow(x, y))
        output("_test_output", math.fmod(x, y))

    pairs = [(2.0, 3.0), (-7.0, 2.0), (7.0, -2.0)]
    expected = [[pymath.pow(x, y), pymath.fmod(x, y)] for x, y in pairs]
    run_float_fn_approx_per_shot(
        main, expected, args=[{"x": x, "y": y} for x, y in pairs]
    )


def test_atan_range(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float) -> None:
        output("_test_output", math.atan(x))

    # https://go.dev/src/math/atan.go: range reduction and large finite inputs.
    xs = [
        -sys.float_info.max,
        -2.5,
        -1.5,
        -0.66,
        0.66,
        1.5,
        2.5,
        sys.float_info.max,
    ]
    run_float_fn_approx_per_shot(
        main, [pymath.atan(x) for x in xs], args=[{"x": x} for x in xs], rel=2e-14
    )


def test_trig_angle_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float) -> None:
        output("_test_output", math.sin(angle(x)))
        output("_test_output", math.cos(angle(x)))
        output("_test_output", math.tan(angle(x)))

    halfturns = [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0]
    expected = [
        [getattr(pymath, name)(x * pymath.pi) for name in ["sin", "cos", "tan"]]
        for x in halfturns
    ]
    run_float_fn_approx_per_shot(
        main,
        expected,
        args=[{"x": x} for x in halfturns],
        rel=2e-14,
        abs=pymath.ulp(0.0),
    )


def test_inverse_trig_angle_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(x: float) -> None:
        asin_result: angle = math.asin(x)
        acos_result: angle = math.acos(x)
        atan_result: angle = math.atan(x)
        output("_test_output", asin_result.halfturns)
        output("_test_output", acos_result.halfturns)
        output("_test_output", atan_result.halfturns)

    xs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    expected = [
        [getattr(pymath, name)(x) / pymath.pi for name in ["asin", "acos", "atan"]]
        for x in xs
    ]
    run_float_fn_approx_per_shot(
        main, expected, args=[{"x": x} for x in xs], rel=2e-14, abs=pymath.ulp(0.0)
    )


def test_atan2_angle_emulation(run_float_fn_approx_per_shot):
    @guppy
    def main(y: float, x: float) -> None:
        result: angle = math.atan2(y, x)
        output("_test_output", result.halfturns)

    args = [
        {"y": y, "x": x} for y in [-2.0, -0.0, 0.0, 2.0] for x in [-1.0, -0.0, 0.0, 1.0]
    ]
    run_float_fn_approx_per_shot(
        main,
        [
            pymath.atan2(shot_args["y"], shot_args["x"]) / pymath.pi
            for shot_args in args
        ],
        args=args,
        rel=2e-14,
        abs=pymath.ulp(0.0),
    )


def test_inverse_trig_angle_return(validate):
    @guppy
    def main(x: float) -> tuple[angle, angle, angle]:
        return math.asin(x), math.acos(x), math.atan(x)

    validate(main.compile_function())


def test_atan2_angle_return(validate):
    @guppy
    def main(y: float, x: float) -> angle:
        return math.atan2(y, x)

    validate(main.compile_function())
