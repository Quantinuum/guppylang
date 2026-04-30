from typing import Generic
import pytest
from guppylang.decorator import guppy
from collections.abc import Callable


def test_staticmethod_struct_generic(validate):
    T = guppy.type_var("T")

    @guppy.struct
    class Test(Generic[T]):
        @guppy
        @staticmethod
        def default(a: T) -> "Test[T]":
            return Test()

    @guppy
    def main() -> None:
        t = Test.default(1.0)
        # can call Test.default[int] from Test[float] instance
        # as static methods ignore instance types
        t.default(3)

    validate(main.compile())


def test_staticmethod_higher_order(validate):

    @guppy.struct
    class Test:
        a: int
        b: float

        @guppy
        @staticmethod
        def new(a: int, b: float) -> "Test":
            return Test(a, a + b)

    @guppy
    def takes_constructor(constructor: Callable[[int, float], Test]) -> None:
        constructor(1, 1.0)

    @guppy
    def main() -> None:
        custom_constructor = Test.new
        takes_constructor(custom_constructor)

    validate(main.compile())


@pytest.mark.xfail(reason="Static comptime functions not yet supported")
def test_staticmethod_comptime(validate):

    @guppy.struct
    class Test:
        @guppy.comptime
        @staticmethod
        def gives_int() -> int:
            return 3

    @guppy
    def main() -> None:
        a = Test.gives_int()

    validate(main.compile())


def test_staticmethod_enum(validate):

    @guppy.enum
    class MyEnum:
        @guppy
        @staticmethod
        def smethod() -> None:
            pass

    @guppy
    def main() -> None:
        MyEnum.smethod()

    validate(main.compile())


def test_staticmethod_enum_instantiated(validate):

    @guppy.enum
    class MyEnum:
        VariantA = {}  # noqa: RUF012
        VariantB = {"x": int}  # noqa: RUF012

        @guppy
        @staticmethod
        def smethod() -> int:
            return 2

    @guppy
    def main() -> None:
        e = MyEnum.VariantA()
        e.smethod()

    validate(main.compile())


def test_staticmethod_overload(validate):
    @guppy.struct
    class Test:
        @guppy
        @staticmethod
        def func1(b: float) -> None:
            pass

        @guppy
        @staticmethod
        def func2(a: int) -> None:
            pass

        @guppy.overload(func1, func2)
        @staticmethod
        def overloaded() -> None: ...

    @guppy
    def main() -> None:
        t = Test()
        Test.overloaded(3)
        Test.overloaded(2.0)

    validate(main.compile())
