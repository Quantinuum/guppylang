from typing import Generic

from guppylang.decorator import guppy
from guppylang.std.builtins import array, comptime, nat


def test_generic_nats(run_int_fn):
    n = guppy.nat_var("n")
    m = guppy.nat_var("m")

    @guppy.comptime
    def foo(_xs: array[int, n], _ys: array[int, m]) -> int:
        assert isinstance(n, int)
        assert isinstance(m, int)
        return n + m

    @guppy
    def main() -> int:
        a = foo(array(1), array(1, 2))
        b = foo(array(1, 2, 3), array(1, 2, 3, 4))
        return a + b

    run_int_fn(main, 1 + 2 + 3 + 4)


def test_comptime_args(run_float_fn_approx):
    @guppy.comptime
    def foo(x: float @ comptime, b: bool @ comptime) -> float:
        assert isinstance(x, float)
        assert isinstance(b, bool)
        return x if b else -x

    @guppy
    def main() -> float:
        return foo(1.5, True) + foo(1.0, False)

    run_float_fn_approx(main, 0.5)


def test_dependent(run_float_fn_approx):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy.comptime
    def foo(x: T @ comptime) -> T:
        return x

    @guppy
    def main() -> float:
        return foo(0.5) if foo(True) else 0.0

    run_float_fn_approx(main, 0.5)


def test_method(run_int_fn):
    T = guppy.type_var("T")
    n = guppy.nat_var("n")

    @guppy.struct
    class S(Generic[T, n]):
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
