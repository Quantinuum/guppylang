"""Tests for using Python expressions in Guppy functions with generics only introduced
in Python 3.12."""

from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.builtins import comptime, nat
from guppylang.std.lang import Copy, owned
from guppylang.std.platform import result


def test_generic(validate):
    @guppy
    def foo[n: nat]() -> None:
        pass

    N = 100

    @guppy
    def main() -> None:
        foo[N]()

    validate(main.compile_function())


def test_use_generic(run_int_fn):
    n = 0  # Test that this n is not captured

    @guppy
    def foo[n: nat, m: nat]() -> int:
        return int(comptime(n - m + 1))

    @guppy
    def main() -> int:
        return foo[20, 10]()

    run_int_fn(main, 11)


def test_comptime_signatures(validate):
    @guppy
    def double[T: Copy, n: nat](xs: array[T, n]) -> array[T, "comptime(2 * n)"]:
        return array(xs[i // 2] for i in range(comptime(n + n)))  # n + n = 2n

    @guppy
    def concat[n: nat, m: nat](
        xs: array[int, n], ys: array[int, m]
    ) -> array[int, "comptime(n + m)"]:
        res = array(0 for _ in range(comptime(n + m)))
        for i in range(n):
            res[i] = xs[i]
        for i in range(m):
            res[n + i] = ys[i]
        return res

    @guppy
    def flatten[T: Copy, n: nat, m: nat](
        xs: array[array[T, m], n],
    ) -> array[T, "comptime(n * m)"]:
        return array(xs[i // m][i % m] for i in range(comptime(n * m)))

    @guppy
    def test_empty() -> None:
        empty: array[int, 0] = array()
        empty2: array[array[int, 0], 0] = array()

        a: array[int, 0] = double(empty)
        b: array[int, 0] = concat(empty.copy(), empty)
        c: array[int, 0] = flatten(empty2)
        d: array[int, 0] = flatten(array(empty.copy()))
        e: array[int, 0] = flatten(array(empty.copy(), empty))

    @guppy
    def main() -> None:
        test_empty()

        result("a", double(array(1)))
        result("b", double(array(1.0, 2.0)))

        result("c", concat(array(1, 2), array()))
        result("d", concat(array(1), array(2, 3, 4)))

        result("e", flatten(array(array(True))))
        result("f", flatten(array(array(1, 2), array(3, 4))))
        result("g", flatten(array(array(1, 2, 3), array(4, 5, 6), array(7, 8, 9))))

    assert dict(main.emulator(n_qubits=1).run().results[0].entries) == {
        "a": [1, 1],
        "b": [1.0, 1.0, 2.0, 2.0],
        "c": [1, 2],
        "d": [1, 2, 3, 4],
        "e": [1],
        "f": [1, 2, 3, 4],
        "g": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }


def test_comptime_signature2(validate):
    @guppy.declare
    def halve[T, n: nat](xs: array[T, "comptime(2 * n)"] @ owned) -> array[int, n]: ...

    @guppy.declare
    def double[T, n: nat](
        xs: array[T, "comptime(n // 2)"] @ owned,
    ) -> array[int, n]: ...

    @guppy
    def identity1[T, n: nat](xs: array[T, n] @ owned) -> array[T, n]:
        return halve[T, n](double[T, comptime(2 * n)](xs))

    @guppy
    def identity2[T, n: nat](
        xs: array[T, "comptime(2 * n)"] @ owned,
    ) -> array[T, "comptime(2 * n)"]:
        return double[T, comptime(2 * n)](halve[T, n](xs))

    @guppy
    def main() -> None:
        identity1[int, 0](array())
        identity2[int, 0](array())

        identity1[int, 1](array(1))

        identity1[int, 2](array(1, 2))
        identity2[int, 1](array(1, 2))

    validate(main.compile())


def test_dodgy_type_level_arithmetic(validate):
    @guppy
    def foo[n: nat]() -> array[int, "comptime(2 * n)"]:
        # This is wrong, but only for certain values of n:
        return array(0 for _ in range(comptime(n**2)))

    @guppy
    def tail[T, n: nat](xs: array[T, n] @ owned) -> array[T, "comptime(n - 1)"]:
        # This is only allowed for n > 0
        _, *ys = xs
        return ys

    @guppy
    def main() -> None:
        foo[0]()  # Ok since 2*0 = 0^2
        foo[2]()  # Ok since 2*2 = 2^2

        tail(array(1))
        tail(array(1, 2, 3))

    validate(main.compile())


def test_comptime_arg_inference(validate):
    @guppy
    def tail[T](
        n: nat @ comptime,
        xs: array[T, "comptime(n + 1)"] @ owned,  # noqa: F821
    ) -> "array[T, n]":  # noqa: F821
        # Type system guarantees that this always works, but requires an extra
        # comptime argument
        _, *ys = xs
        return ys

    @guppy
    def main() -> None:
        tail(0, array(1))
        tail(2, array(1, 2, 3))

    validate(main.compile())
