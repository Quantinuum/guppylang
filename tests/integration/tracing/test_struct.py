from collections.abc import Callable
from typing import Generic

from guppylang.decorator import guppy


def test_create(run_int_fn):
    @guppy.struct
    class S:
        x: int
        y: int

    @guppy.comptime
    def main(x: int) -> int:
        s = S(x, 2)
        return s.x + s.y

    run_int_fn(main, 42, args=[40])


def test_argument(run_int_fn):
    @guppy.struct
    class S:
        x: int
        y: int

    @guppy.comptime
    def foo(s: S) -> int:
        return s.x + s.y

    @guppy
    def main() -> int:
        return foo(S(40, 2))

    run_int_fn(main, 42)


def test_write(run_int_fn):
    @guppy.struct
    class S:
        x: int
        y: int

    @guppy.comptime
    def main(y: int) -> int:
        s = S(40, y)
        t = s
        t.y += 1
        return s.x + s.y

    run_int_fn(main, 42, args=[1])


def test_method(run_int_fn):
    @guppy.struct
    class S:
        x: int
        y: int

        @guppy.comptime
        def get_x(self: "S") -> int:
            return self.x

        @guppy
        def get_y(self: "S") -> int:
            return self.y

    @guppy.comptime
    def main(x: int, y: int) -> int:
        s = S(x, y)
        return s.get_x() + s.get_y()

    run_int_fn(main, 42, args=[40, 2])


def test_generic_nested(validate, run_float_fn_approx):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.struct
    class StructA(Generic[T]):
        x: tuple[int, T]

    @guppy.struct
    class StructB(Generic[S, T]):
        x: S
        y: StructA[T]

    @guppy.comptime
    def foo(a: StructA[StructA[float]], b: StructB[bool, int]) -> float:
        flat_a = a.x[0] + a.x[1].x[0] + a.x[1].x[1]
        flat_b = b.y.x[0] + b.y.x[1]
        return flat_a + flat_b

    @guppy.comptime
    def bar(
        x1: int, x2: int, x3: float, x4: int, x5: int
    ) -> tuple[StructA[StructA[float]], StructB[bool, int]]:
        a = StructA((x1, StructA((x2, x3))))
        b = StructB(True, StructA((x4, x5)))
        return a, b

    @guppy
    def main() -> float:
        a, b = bar(1, 10, 100, 1000, 10000)
        return foo(a, b)

    run_float_fn_approx(main, 11111)


def test_load_constructor(validate):
    @guppy.struct
    class S:
        x: int

    @guppy.comptime
    def test() -> Callable[[int], S]:
        return S

    validate(test.compile_function())
