import pytest

from guppylang.decorator import guppy
from guppylang.emulator import EmulatorError
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import nat
from tests.util import compile_guppy


def test_negative(run_int_fn):
    @guppy
    def negative() -> int:
        return 2 - 42

    run_int_fn(negative, expected=-40)


def test_arith_basic(run_int_fn):
    @guppy
    def add(x: int, y: int) -> int:
        return x + y

    @guppy
    def main() -> int:
        return add(40, 2)

    run_int_fn(main, 42)


def test_constant(validate):
    @compile_guppy
    def const() -> float:
        return 42.0

    validate(const)


def test_nat_literal(validate):
    @compile_guppy
    def const() -> nat:
        return 42

    validate(const)


def test_int_bounds(run_int_fn):
    @guppy
    def main() -> int:
        return 9_223_372_036_854_775_807 + -9_223_372_036_854_775_808

    run_int_fn(main, -1)


def test_nat_bounds(run_int_fn):
    @guppy
    def main() -> nat:
        x: nat = 18_446_744_073_709_551_614
        return x - x

    run_int_fn(main, 0)


def test_aug_assign(run_int_fn):
    @guppy
    def add(x: int) -> int:
        x += 1
        return x

    @guppy
    def main() -> int:
        return add(5)

    run_int_fn(main, 6)


def test_nat(validate):
    @compile_guppy
    def foo(
        a: nat, b: nat, c: bool, d: int, e: float
    ) -> tuple[nat, bool, int, float, float]:
        b, c, d, e = nat(b), nat(c), nat(d), nat(e)
        x = a + b * c // d - e
        y = e / b % a
        return x, bool(x), int(x), float(x), y

    validate(foo)


def test_nat2(validate):
    @compile_guppy
    def foo(
        a: nat, b: nat, c: bool, d: int, e: float
    ) -> tuple[nat, bool, int, float, float]:
        b, c, d, e = nat(b), nat(c), nat(d), nat(e)
        x = a + b * c // d - e
        y = e / b
        return x, bool(x), int(x), float(x), y

    validate(foo)


def test_float_coercion(validate):
    @compile_guppy
    def coerce(x: int, y: float) -> float:
        return x * y

    validate(coerce)


def test_arith_big(validate):
    @compile_guppy
    def arith(x: int, y: float, z: int) -> bool:
        a = x // y + 3 * z
        b = -8 >= a > 5 or (x * y == 0 and a % 3 < x)
        return b

    validate(arith)


def test_angle_arith(validate):
    @guppy
    def main(a1: angle, a2: angle) -> bool:
        a3 = -a1 + a2 * -3
        a3 -= a1
        a3 += 2 * a1
        return a3 / 3 == -a2

    validate(main.compile_function())


def test_angle_arith_float(validate):
    @guppy
    def main(a1: angle, a2: angle) -> bool:
        a3 = -a1 + a2 * -3.5
        a3 -= a1
        a3 += 2.2 * a1
        return a3 / 3.9 == -a2

    validate(main.compile_function())


def test_implicit_coercion(validate):
    @compile_guppy
    def coerce(x: nat) -> float:
        y: int = x
        z: float = y
        a: float = 1
        return z + a

    validate(coerce)


def test_angle_float_coercion(validate):
    @guppy
    def main(f: float) -> tuple[angle, float]:
        a = angle(f)
        return a, float(a)

    validate(main.compile_function())


def test_angle_pi(validate):
    @guppy
    def main() -> angle:
        a = 2 * pi
        a += -pi / 3
        a += 3 * pi / 2
        return a

    validate(main.compile_function())


def test_shortcircuit_assign1(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if (z := x) and y > 0:
            return z
        return not z

    validate(foo)


def test_shortcircuit_assign2(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if y > 0 and (z := x):
            return z
        return False

    validate(foo)


def test_shortcircuit_assign3(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if (z := x) or y > 0:
            return z
        return z

    validate(foo)


def test_shortcircuit_assign4(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if y > 0 or (z := x):
            return False
        return z

    validate(foo)


def test_supported_ops(run_int_fn):
    @guppy
    def double_add(x: int) -> int:
        return x + x

    @guppy
    def double_mul(x: int) -> int:
        return x * 2

    @guppy
    def quad(x: int) -> int:
        y = double_add(x)
        z = double_mul(x)
        return y + z

    @guppy
    def run_quad() -> int:
        return quad(42)

    @guppy
    def neg(x: int) -> int:
        return -x

    @guppy
    def run_neg() -> int:
        return neg(42)

    @guppy
    def div(x: int, y: int) -> int:
        return x // y

    @guppy
    def run_div() -> int:
        return div(-42, 21)

    @guppy
    def run_rem() -> int:
        return 11 % 3

    run_int_fn(run_quad, expected=168)
    run_int_fn(run_neg, expected=-42)
    run_int_fn(run_div, expected=-2)
    run_int_fn(run_rem, expected=2)


def test_angle_exec(run_float_fn_approx):
    @guppy
    def main() -> float:
        a1 = pi
        a2 = pi * 2
        a3 = -a1 + a2 * -3
        a3 -= a1
        a3 += 2 * a1
        return float(a3)

    import math

    run_float_fn_approx(main, expected=-6 * math.pi)


def test_xor(run_int_fn):
    @guppy
    def main1() -> int:
        return int(True ^ False ^ False)  # noqa: RUF046

    run_int_fn(main1, 1)

    @guppy
    def main2() -> int:
        return int(True ^ False ^ False ^ True)  # noqa: RUF046

    run_int_fn(main2, 0)


def test_bool_rand(run_int_fn):
    @guppy
    def main1() -> int:
        x: bool = True
        return int(x.__rand__(False))

    run_int_fn(main1, 0)

    @guppy
    def main2() -> int:
        x: bool = True
        return int(x.__rand__(True))

    run_int_fn(main2, 1)


def test_bool_ror(run_int_fn):
    @guppy
    def main1() -> int:
        x: bool = False
        return int(x.__ror__(True))

    run_int_fn(main1, 1)

    @guppy
    def main2() -> int:
        x: bool = False
        return int(x.__ror__(False))

    run_int_fn(main2, 0)


def test_bool_rxor(run_int_fn):
    @guppy
    def main1() -> int:
        x: bool = True
        return int(x.__rxor__(True))

    run_int_fn(main1, 0)

    @guppy
    def main2() -> int:
        x: bool = True
        return int(x.__rxor__(False))

    run_int_fn(main2, 1)


def test_pow(run_int_fn) -> None:
    @guppy
    def main() -> int:
        return -(3**3) + 4**2

    run_int_fn(main, -11)


def test_float_to_int(run_int_fn) -> None:
    @guppy
    def main() -> int:
        return int(-2.75)

    run_int_fn(main, -2)


def test_nat_to_int(run_int_fn) -> None:
    @guppy
    def main() -> int:
        return int(nat(2))

    run_int_fn(main, 2)


def test_int_to_nat(run_int_fn) -> None:
    @guppy
    def main() -> nat:
        return nat(2)

    run_int_fn(main, 2)


# TODO this should be a compile-time error
def test_int_to_nat_negative(run_int_fn) -> None:
    @guppy
    def main() -> nat:
        return nat(-2)

    with pytest.raises(EmulatorError, match="is_to_u called on negative value"):
        run_int_fn(main, None)


def test_float_to_nat(run_int_fn) -> None:
    @guppy
    def main() -> nat:
        return nat(2.75)

    run_int_fn(main, 2)


def test_shift(run_int_fn) -> None:
    @guppy
    def main() -> int:
        nats = (nat(7) << nat(2)) - (nat(1) << nat(3))
        return int(nats) + (2 << 3) + (53 >> 3)

    run_int_fn(main, 42)


def test_divmod(run_int_fn) -> None:
    @guppy
    def quot() -> int:
        return -1 // 4

    @guppy
    def rem() -> int:
        return -1 % 4

    run_int_fn(quot, -1)
    run_int_fn(rem, 3)
