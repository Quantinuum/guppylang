from typing import Generic
import pytest
from guppylang.decorator import guppy
from collections.abc import Callable

# TEST GENERIC
# and test specifying types in generic staticmethods
# test using staticfunctions as higher order methods
# test other guppy decorators
# guppy.declare
# guppy.comptime
# guppy.overload ? I don't even know if these work with methods
# Looks like guppy.overload does not work with methods
# seems like they could easily break with impls
# check with someone about guppy.wasm_module
# try testing for enums?


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


@pytest.mark.xfail(reason="Not yet supported")
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


@pytest.mark.xfail(reason="Attribute visitor for enums currently only manages variants")
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

    validate(MyEnum.smethod())
