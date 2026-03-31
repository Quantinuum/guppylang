from collections.abc import Callable
from typing import Generic

from guppylang.decorator import guppy


def test_create(validate):
    @guppy.enum
    class MyEnum:
        Empty = {}  # noqa: RUF012
        WithField = {"x": int}  # noqa: RUF012

    @guppy.comptime
    def main() -> None:
        e1 = MyEnum.Empty()
        e2 = MyEnum.WithField(42)

    validate(main.compile_function())


def test_argument(validate):
    @guppy.enum
    class MyEnum:
        VariantA = {"x": int}  # noqa: RUF012

    @guppy.comptime
    def foo(e: MyEnum) -> MyEnum:
        return e

    @guppy
    def main() -> MyEnum:
        return foo(MyEnum.VariantA(42))

    validate(main.compile_function())


def test_comptime_method(run_int_fn):
    @guppy.enum
    class MyEnum:
        VariantA = {}  # noqa: RUF012
        VariantB = {"x": int}  # noqa: RUF012

        @guppy.comptime
        def const(self: "MyEnum") -> int:
            return 42

    @guppy.comptime
    def main() -> int:
        e = MyEnum.VariantB(5)
        return e.const()

    run_int_fn(main, 42)


def test_mixed_methods(run_int_fn):
    @guppy.enum
    class MyEnum:
        VariantA = {"x": int}  # noqa: RUF012

        @guppy.comptime
        def get_const(self: "MyEnum") -> int:
            return 40

        @guppy
        def add_two(self: "MyEnum", y: int) -> int:
            return 2 + y

    @guppy.comptime
    def main() -> int:
        e = MyEnum.VariantA(5)
        return e.get_const() + e.add_two(0)

    run_int_fn(main, 42)


def test_generic(validate):
    T = guppy.type_var("T")
    S = guppy.type_var("S")

    @guppy.enum
    class EnumA(Generic[T]):
        VariantA = {"x": tuple[int, T]}  # noqa: RUF012

        @guppy
        def m(self: "EnumA[T]") -> int:
            return 0

    @guppy.enum
    class EnumB(Generic[S, T]):
        VariantA = {"x": S, "y": EnumA[T]}  # noqa: RUF012

        @guppy
        def m(self: "EnumB[S, T]") -> int:
            return 1

    @guppy.comptime
    def main(a: EnumA[EnumA[float]], b: EnumB[bool, int]) -> None:
        a.m()
        b.m()

    validate(main.compile_function())


def test_load_constructor(validate):
    @guppy.enum
    class MyEnum:
        VariantA = {"x": int}  # noqa: RUF012

    @guppy.comptime
    def test() -> Callable[[int], MyEnum]:
        return MyEnum.VariantA

    validate(test.compile_function())


def test_tuple_unpacking_variants(validate):
    @guppy.enum
    class MyEnum:
        A, B = {}, {}

    @guppy.comptime
    def main() -> None:
        a = MyEnum.A()
        b = MyEnum.B()

    validate(main.compile_function())
