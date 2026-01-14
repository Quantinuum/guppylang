from guppylang.decorator import guppy
from guppylang.std.builtins import nat
from guppylang.std.num import bytecast_nat_to_float, bytecast_float_to_nat


def test_roundtrip(run_int_fn):
    @guppy
    def roundtrip(n: nat) -> nat:
        f = bytecast_nat_to_float(n)
        return bytecast_float_to_nat(f)

    @guppy
    def main() -> nat:
        x = roundtrip(42)
        return x

    run_int_fn(main, expected=42)


def test_roundtrip2(run_float_fn_approx):
    @guppy
    def roundtrip(f: float) -> float:
        n = bytecast_float_to_nat(f)
        f2 = bytecast_nat_to_float(n)
        n2 = bytecast_float_to_nat(f2)
        return bytecast_nat_to_float(n2)

    @guppy
    def main() -> float:
        x = roundtrip(42.0)
        return x

    run_float_fn_approx(main, expected=42.0)
