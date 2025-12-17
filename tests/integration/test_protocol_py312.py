from guppylang.decorator import guppy
import pytest


def test_def():
    @guppy.protocol
    class MyProto:
        def foo(self: "MyProto") -> "MyProto": ...

        # TODO: Implement Self support for protocols.
        # def bar(self: Self) -> Self: ...

        # Internally desugared this is equivalent to `foo`.
        def baz[M: MyProto](self: M) -> M: ...

    MyProto.compile()


def test_def_parameterised():
    @guppy.protocol
    class MyProto[T]:
        def foo(self: "MyProto[T]", x: T) -> T: ...

        # TODO: Implement Self support for protocols.
        # def bar(self: Self) -> "MyProto": ...

        def baz[M: MyProto[T]](self: M, y: int) -> int: ...

    MyProto.compile()


def test_use_def_as_type():
    @guppy.protocol
    class MyProto:
        def foo(self: "MyProto") -> "MyProto": ...

    @guppy.declare
    def bar(a: MyProto) -> MyProto: ...

    @guppy.declare
    def baz[M: MyProto](a: M) -> M: ...

    bar.compile()
    baz.compile()


def test_use_def_as_type_parameterised():
    @guppy.protocol
    class MyProto[T, S]:
        def foo(self: "MyProto[T, S]") -> "MyProto[T, S]": ...

    T = guppy.type_var("T")
    S = guppy.type_var("S")

    @guppy.declare
    def baz1(a: MyProto[T, S]) -> MyProto[T, S]: ...

    @guppy.declare
    def baz2(a: MyProto[bool, bool]) -> MyProto[int, int]: ...

    baz1.compile()
    baz2.compile()


def test_basic(validate):
    @guppy.protocol
    class MyProto:
        def foo(self: "MyProto", x: int) -> str: ...

    @guppy.struct
    class MyType:
        @guppy
        def foo(self: "MyType", x: int) -> str:
            return str(x)

    @guppy
    def bar[M: MyProto](a: M) -> str:
        return a.foo(42)

    # Internally desugared this should be equivalent to `bar`.
    @guppy
    def baz(a: MyProto) -> str:
        return a.foo(42)

    @guppy
    def main() -> None:
        mt = MyType()
        bar(mt)
        baz(mt)

    # TODO: Turn into compile once compilation is implemented.
    validate(main.check())


def test_basic_parameterised(validate):
    @guppy.protocol
    class MyProto[T, S]:
        def foo(self: "MyProto[T, S]", x: T) -> S: ...

    @guppy.struct
    class MyType[P: int, Q: str]:
        @guppy
        def foo(self: "MyType[P, Q]", x: int) -> str:
            return str(x)

    @guppy.struct
    class MyOtherType[P: int, Q: int]:
        @guppy
        def foo(self: "MyType[P, Q]", x: int) -> int:
            return x * 2

    T = guppy.type_var("T")
    S = guppy.type_var("S")

    @guppy
    def baz1(a: MyProto[T, S], x: T) -> S:
        return a.foo(x)

    @guppy
    def baz2(a: MyProto[int, str]) -> str:
        return a.foo(42)

    @guppy
    def baz3(a: MyProto[T, S]) -> str:
        return a.foo(42)

    @guppy
    def main() -> str:
        mt = MyType()
        baz1(mt, 42)
        baz2(mt)
        baz3(mt)
        mot = MyOtherType()
        baz1(mot, 42)
        # baz2(mt) # should fail

    # TODO: Turn into compile once compilation is implemented.
    validate(main.check())
