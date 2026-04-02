from guppylang.decorator import guppy
from guppylang.std.builtins import array, comptime, nat
from guppylang.std.lang import Copy, Drop


def test_generic_nats(run_int_fn):
    @guppy.comptime
    def foo[n: nat, m: nat]() -> int:
        assert isinstance(n, int)
        assert isinstance(m, int)
        return n + m

    @guppy
    def main() -> int:
        return foo[1, 10]() + foo[100, 1000]()

    run_int_fn(main, 1111)


def test_generic_float_bool(run_float_fn_approx):
    @guppy.comptime
    def foo[x: float, b: bool]() -> float:
        assert isinstance(x, float)
        assert isinstance(b, bool)
        return x if b else -x

    @guppy
    def main() -> float:
        return foo[1.5, True]() + foo[1.0, False]()

    run_float_fn_approx(main, 0.5)


def test_dependent(run_float_fn_approx):
    @guppy.comptime
    def foo[T: (Copy, Drop), x: T]() -> T:
        return x

    @guppy
    def main() -> float:
        return foo[float, 0.5]() if foo[bool, True]() else 0.0

    run_float_fn_approx(main, 0.5)


def test_method(run_int_fn):
    @guppy.struct
    class S[T, n: nat]:
        x: T

        @guppy.comptime
        def foo(self) -> int:
            assert isinstance(n, int)
            return 2 * n

    @guppy
    def main() -> int:
        s = S[float, 21](1.0)
        return s.foo()

    run_int_fn(main, 42)


def test_mixed(run_int_fn):
    n = guppy.nat_var("n")

    @guppy.comptime
    def foo[m: nat](xs: array[int, n], ys: array[int, m], k: int @ comptime) -> int:
        assert isinstance(n, int)
        assert isinstance(m, int)
        assert isinstance(k, int)
        return n + m + k

    @guppy
    def main() -> int:
        return foo(array(1), array(1, 2), 3)

    run_int_fn(main, 6)
