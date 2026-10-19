"""Tests for using Python expressions in Guppy functions with generics only introduced
in Python 3.12."""

import pytest

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


def test_generic_struct(validate):
    @guppy.struct
    class MyStruct[n: nat]:
        xs: array[int, "comptime(n + 1)"]

    @guppy
    def make[n: nat]() -> MyStruct[n]:
        return MyStruct[n](array(0 for _ in range(comptime(n + 1))))

    @guppy
    def main() -> array[int, 11]:
        a = make[10]()
        b = make[11]()
        _, *ys = b.xs
        a.xs = ys
        return a.xs

    validate(main.compile())


@pytest.mark.parametrize(("n", "m"), [(0, 0), (0, 3), (2, 3), (3, 2)])
def test_generic_struct_multiple_params(run_int_fn, n, m):
    @guppy.struct
    class Buffers[T: Copy, n: nat, m: nat]:
        xs: array[T, "comptime(n + m)"]
        ys: array[T, "comptime(n * m)"]

    @guppy
    def make[T: Copy, n: nat, m: nat](x: T) -> Buffers[T, n, m]:
        return Buffers[T, n, m](
            array(x for _ in range(comptime(n + m))),
            array(x for _ in range(comptime(n * m))),
        )

    @guppy
    def main() -> int:
        a = make[int, n, m](7)
        b = make[bool, m, n](True)
        total = len(a.xs) + len(a.ys) + len(b.xs) + len(b.ys)
        for x in a.xs:
            total += x
        for y in b.ys:
            total += int(y)
        return total

    run_int_fn(main, 2 * (n + m + n * m) + 7 * (n + m) + n * m)


def test_generic_struct_comptime_scope(run_int_fn):
    n = 100  # The struct parameter must shadow this captured Python variable.
    scale = 2

    def size(n):
        return scale * n + 1

    @guppy.struct
    class Buffer[n: nat]:
        xs: array[int, "comptime(size(n))"]

    @guppy
    def main() -> int:
        a = Buffer[2](array(1, 2, 3, 4, 5))
        b = Buffer[0](array(6))
        return a.xs[4] + b.xs[0]

    run_int_fn(main, 11)


def test_generic_struct_nested_array(run_int_fn):
    @guppy.struct
    class Matrix[n: nat, m: nat]:
        rows: array[array[int, "comptime(m + 1)"], "comptime(n + 1)"]

    @guppy
    def make[n: nat, m: nat]() -> Matrix[n, m]:
        return Matrix[n, m](
            array(
                array(i * 10 + j for j in range(comptime(m + 1)))
                for i in range(comptime(n + 1))
            ),
        )

    @guppy
    def main() -> int:
        a = make[2, 3]()
        b = make[3, 2]()
        return a.rows[2][3] + b.rows[3][2]

    run_int_fn(main, 55)


def test_generic_struct_nested(validate):
    @guppy.struct
    class Inner[n: nat]:
        xs: array[int, "comptime(n + 1)"]

    @guppy.struct
    class Outer[n: nat]:
        inner: Inner[n]

    @guppy
    def main() -> array[int, 3]:
        outer = Outer[2](Inner[2](array(1, 2, 3)))
        return outer.inner.xs

    validate(main.compile())


def test_generic_struct_nested_comptime_arg(validate):
    @guppy.struct
    class Inner[n: nat]:
        xs: array[int, "comptime(n + 1)"]

    @guppy.struct
    class Outer[n: nat]:
        inner: Inner["comptime(n * 2)"]

    @guppy
    def main() -> array[int, 5]:
        outer = Outer[2](Inner[4](array(1, 2, 3, 4, 5)))
        return outer.inner.xs

    validate(main.compile())


def test_generic_struct_method(run_int_fn):
    @guppy.struct
    class Buffer[T: Copy, n: nat]:
        xs: array[T, "comptime(n + 1)"]

        @guppy
        def first(self) -> T:
            return self.xs[0]

        @guppy
        def replace(self, xs: array[T, "comptime(n + 1)"] @ owned) -> None:
            self.xs = xs

    @guppy
    def main() -> int:
        a = Buffer[int, 2](array(1, 2, 3))
        b = Buffer[bool, 0](array(False))
        a.replace(array(4, 5, 6))
        b.replace(array(True))
        return a.first() + int(b.first())

    run_int_fn(main, 5)
