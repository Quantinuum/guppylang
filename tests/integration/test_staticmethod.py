from guppylang.library import GuppyLibrary, link_name
from guppylang.std.builtins import result, output
from typing import Generic
import pytest
from guppylang.decorator import guppy
from collections.abc import Callable
from typing import Self


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
        VariantA = {}
        VariantB = {"x": int}

        @guppy
        @staticmethod
        def smethod() -> int:
            return 2

    @guppy
    def main() -> None:
        e = MyEnum.VariantA()
        e.smethod()

    validate(main.compile())


def test_staticmethod_self(validate):

    @guppy.struct(frozen=True)
    class Test:
        @guppy
        @staticmethod
        def foo() -> Self:
            return Test()

    @guppy
    def main() -> None:
        t = Test()
        t.foo()
        Test.foo()

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


def test_library_staticmethod():
    @guppy.struct
    @link_name("super_struct")
    class MyStruct:
        @guppy
        @staticmethod
        def super_func(a: int) -> int:
            return 5

    lib = GuppyLibrary.from_members(MyStruct).compile()

    @guppy.struct
    @link_name("super_struct")
    class MyStructInterface:
        @guppy.declare
        @staticmethod
        def super_func(a: int) -> int: ...

    @guppy
    def main() -> None:
        m = MyStructInterface()
        m.super_func(2)
        result("result", MyStructInterface.super_func(1))

    results = (
        main.emulator(n_qubits=1, libs=[lib]).coinflip_sim().run().results[0].entries
    )
    assert results == [("result", 5)]


def test_staticmethod_protocol_basic(validate):

    @guppy.protocol
    class MyProto:
        @guppy.require
        @staticmethod
        def foo(x: int) -> str: ...

    @guppy.struct(frozen=True)
    class Test:
        @guppy
        @staticmethod
        def foo(x: int) -> str:
            output("out", x)
            return "help"

    @guppy
    def hasmyproto(t: MyProto) -> None:
        t.foo(3)
        MyProto.foo(4)

    @guppy
    def main() -> None:
        t = Test()
        hasmyproto(t)

    validate(main.compile())
    res = main.emulator(1).coinflip_sim().run().results[0].entries
    assert res == [("out", 3), ("out", 4)]


def test_staticmethod_protocol_generic(validate):

    T = guppy.type_var("T")

    @guppy.protocol
    class MyProto(Generic[T]):
        @guppy.require
        @staticmethod
        def foo(arg: T) -> str: ...

    @guppy.struct(frozen=True)
    class Test(Generic[T]):
        @guppy
        @staticmethod
        def foo(arg: T) -> str:
            return "help"

    @guppy
    def hasmyproto(ty: MyProto[T], arg: T) -> None:
        # ty.foo()
        MyProto.foo(arg)

    @guppy
    def main() -> None:
        t = Test[int]()
        hasmyproto(t, 3)
        # inference error can be fixed with
        # hasmyproto[int, Test[int]](t, 3)

    validate(main.compile())


def test_staticmethod_protocol_self(validate):

    @guppy.protocol
    class Default:
        @guppy.require
        @staticmethod
        def foo() -> Self: ...

    @guppy.struct(frozen=True)
    class Test:
        @guppy
        @staticmethod
        def foo() -> Self:
            return Test()

    @guppy
    def hasmyproto(t: Default) -> None:
        t.foo()
        Default.foo()

    @guppy
    def main() -> None:
        t = Test()
        hasmyproto(t)

    validate(main.compile())
