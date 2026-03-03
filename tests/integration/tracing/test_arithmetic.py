from guppylang.decorator import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.num import nat

from hugr.std.int import IntVal


def test_int(run_int_fn):
    @guppy.comptime
    def pos(x: int) -> int:
        return +x

    @guppy.comptime
    def neg(x: int) -> int:
        return -x

    @guppy.comptime
    def add(x: int, y: int) -> int:
        return 1 + (x + (y + 2))

    @guppy.comptime
    def sub(x: int, y: int) -> int:
        return 1 - (x - (y - 2))

    @guppy.comptime
    def mul(x: int, y: int) -> int:
        return 1 * (x * (y * 2))

    @guppy.comptime
    def div(x: int, y: int) -> int:
        return 100 // (x // (y // 2))

    @guppy.comptime
    def mod(x: int, y: int) -> int:
        return 15 % (x % (y % 10))

    @guppy.comptime
    def pow(x: int, y: int) -> int:
        return 4 ** (x ** (y**0))

    run_int_fn(pos, 10, args=[10])
    run_int_fn(neg, -10, args=[10])
    run_int_fn(add, 2, args=[3, -4])
    run_int_fn(sub, -8, args=[3, -4])
    run_int_fn(mul, -24, args=[3, -4])
    run_int_fn(div, 20, args=[25, 10])
    run_int_fn(mod, 7, args=[8, 9])
    run_int_fn(pow, 16, args=[2, 100])


def test_nat(run_nat_fn):
    @guppy.comptime
    def pos(x: nat) -> nat:
        return +x

    @guppy.comptime
    def add(x: nat, y: nat) -> nat:
        return nat(1) + (x + (y + nat(2)))

    @guppy.comptime
    def sub(x: nat, y: nat) -> nat:
        return nat(10) - (x - (y - nat(2)))

    @guppy.comptime
    def mul(x: nat, y: nat) -> nat:
        return nat(1) * (x * (y * nat(2)))

    @guppy.comptime
    def div(x: nat, y: nat) -> nat:
        return nat(100) // (x // (y // nat(2)))

    @guppy.comptime
    def mod(x: nat, y: nat) -> nat:
        return nat(15) % (x % (y % nat(10)))

    @guppy.comptime
    def pow(x: nat, y: nat) -> nat:
        return nat(4) ** (x ** (y ** nat(0)))

    run_nat_fn(pos, 10, args=[10])
    run_nat_fn(add, 10, args=[3, 4])
    run_nat_fn(sub, 9, args=[3, 4])
    run_nat_fn(mul, 24, args=[3, 4])
    run_nat_fn(div, 20, args=[25, 10])
    run_nat_fn(mod, 7, args=[8, 9])
    run_nat_fn(pow, 16, args=[2, 100])


def test_float(validate, run_float_fn_approx):
    @guppy.comptime
    def pos(x: float) -> float:
        return +x

    @guppy.comptime
    def neg(x: float) -> float:
        return -x

    @guppy.comptime
    def add(x: float, y: float) -> float:
        return 1 + (x + (y + 2))

    @guppy.comptime
    def sub(x: float, y: float) -> float:
        return 1 - (x - (y - 2))

    @guppy.comptime
    def mul(x: float, y: float) -> float:
        return 1 * (x * (y * 2))

    @guppy.comptime
    def div(x: float, y: float) -> float:
        return 100 / (x / (y / 2))

    # TODO: Requires lowering of `ffloor` op: https://github.com/quantinuum/hugr/issues/1905
    # @guppy.comptime
    # def floordiv(x: float, y: float) -> float:
    #     return 100 // (x // (y // 2))

    # TODO: Requires lowering of `fpow` op: https://github.com/quantinuum/hugr/issues/1905
    # @guppy.comptime
    # def pow(x: float, y: float) -> float:
    #     return 4 ** (x ** (y ** 0.5))

    run_float_fn_approx(pos, 10.5, args=[10.5])
    run_float_fn_approx(neg, -10.5, args=[10.5])
    run_float_fn_approx(add, 1.5, args=[3, -4.5])
    run_float_fn_approx(sub, -8.5, args=[3, -4.5])
    run_float_fn_approx(mul, -27.0, args=[3, -4.5])
    run_float_fn_approx(div, 400.0, args=[0.5, 4])

    # TODO: Requires lowering of `ffloor` op: https://github.com/quantinuum/hugr/issues/1905
    # emulate_float_fn_approx(div, ..., [...])

    # TODO: Requires lowering of `fpow` op: https://github.com/quantinuum/hugr/issues/1905
    # emulate_float_fn_approx(pow, ..., [...])


def test_angle(validate):
    @guppy.comptime
    def neg(x: angle) -> angle:
        return -x

    @guppy.comptime
    def neg_pi() -> angle:
        return -pi

    @guppy.comptime
    def add(x: angle, y: float) -> angle:
        return pi + (x + angle(y) + pi)

    @guppy.comptime
    def sub(x: float, y: angle) -> angle:
        return pi - (angle(x) - (y - pi))

    @guppy.comptime
    def mul(x: float, y: angle) -> angle:
        return 1.5 * (x * (y * 2))

    @guppy.comptime
    def div(x: angle, y: float) -> angle:
        return x / y

    @guppy
    def main() -> None:
        """Dummy main function"""
        add, sub, mul, div

    validate(main.compile_function())


def test_dunder_coercions(validate):
    @guppy.comptime
    def test1(x: int) -> float:
        return 1.0 + x

    @guppy.comptime
    def test2(x: int) -> float:
        return x + 1.0

    @guppy.comptime
    def test3(x: float) -> float:
        return 1 + x

    @guppy.comptime
    def test4(x: float) -> float:
        return x + 1

    @guppy.comptime
    def test5(x: int, y: float) -> float:
        return x + y

    @guppy.comptime
    def test6(x: float, y: int) -> float:
        return x + y

    @guppy.comptime
    def test7(x: nat, y: float) -> float:
        return x + y

    @guppy.comptime
    def test8(x: float, y: nat) -> float:
        return x + y

    validate(test1.compile_function())
    validate(test2.compile_function())
    validate(test3.compile_function())
    validate(test4.compile_function())
    validate(test5.compile_function())
    validate(test6.compile_function())
    validate(test7.compile_function())
    validate(test8.compile_function())


def test_const(validate):
    x = guppy.constant("x", "int", IntVal(10, 6))

    @guppy.comptime
    def test1() -> int:
        return -x

    @guppy.comptime
    def test2() -> int:
        return 1 + x

    @guppy.comptime
    def test2() -> int:  # noqa: F811
        return x * 2

    @guppy.comptime
    def test3() -> float:
        return 1.5 - x

    @guppy.comptime
    def test4() -> float:
        return x / 0.5

    validate(test1.compile_function())
    validate(test2.compile_function())
    validate(test3.compile_function())
    validate(test4.compile_function())
