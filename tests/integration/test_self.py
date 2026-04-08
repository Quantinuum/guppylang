from typing import Generic
from typing_extensions import Self

from guppylang import guppy


def test_implicit_self(validate):
    @guppy.struct
    class MyStruct:
        @guppy
        def foo(self) -> None:
            pass

    @guppy.enum
    class MyEnum:
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self) -> None:
            pass

    @guppy
    def main(s: MyStruct, e: MyEnum) -> None:
        s.foo()
        e.foo()

    validate(main.compile_function())


def test_implicit_self_generic(validate):
    T = guppy.type_var("T")
    U = guppy.type_var("U")

    @guppy.struct
    class MyStruct(Generic[T, U]):
        x: T
        y: U

        @guppy
        def foo(self, a: U) -> T:
            return self.x

    @guppy.enum
    class MyEnum(Generic[T, U]):
        VariantA = {"x": T, "y": U}  # noqa: RUF012

        @guppy
        def foo(self, a: U) -> int:
            return 2

    @guppy
    def main(s: MyStruct[int, float], e: MyEnum[int, float]) -> int:
        return s.foo(1.5) + e.foo(1.5)

    validate(main.compile_function())


def test_explicit_self(validate):
    @guppy.struct
    class MyStruct:
        @guppy
        def foo(self, other: Self) -> Self:
            return self

    @guppy
    def main(s: MyStruct) -> MyStruct:
        return s.foo(s).foo(s.foo(MyStruct()))

    validate(main.compile_function())

    @guppy.enum
    class MyEnum:
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self, other: Self) -> Self:
            return self

    @guppy
    def main_enum(e: MyEnum) -> MyEnum:
        return e.foo(e).foo(e.foo(MyEnum.VariantA()))

    validate(main_enum.compile_function())


def test_explicit_self_generic(validate):
    T = guppy.type_var("T")

    @guppy.struct
    class MyStruct(Generic[T]):
        x: T

        @guppy
        def foo(self) -> Self:
            return self

    @guppy.enum
    class MyEnum(Generic[T]):
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self) -> Self:
            return self

    @guppy
    def main(s: MyStruct[int], e: MyEnum[int]) -> None:
        s.foo().foo()
        e.foo().foo()

    validate(main.compile_function())


def test_more_generic(validate):
    T = guppy.type_var("T")
    U = guppy.type_var("U")

    @guppy.struct
    class MyStruct(Generic[T]):
        c: bool
        x: T

        @guppy
        def foo(self, a: T, b: U) -> tuple[T, U]:
            if self.c:
                a = self.x
            return a, b

    @guppy.enum
    class MyEnum(Generic[T]):
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self, a: T, b: U) -> tuple[T, U]:
            return a, b

    @guppy
    def main(s: MyStruct[int], e: MyEnum[int]) -> int:
        a, _ = s.foo(42, True)
        a, _ = s.foo(a, 1.5)
        a, b = s.foo(a, s.x)
        c, _ = e.foo(42, True)
        c, _ = e.foo(c, 1.5)
        c, d = e.foo(c, 99)
        return a + b + c + d

    validate(main.compile_function())
