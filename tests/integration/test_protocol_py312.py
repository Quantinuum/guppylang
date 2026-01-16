from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.lang import owned


def test_def():
    @guppy.protocol
    class MyProto:
        def foo(self: "MyProto") -> "MyProto": ...

        # TODO: Implement Self support for protocols.
        # def bar(self: Self) -> Self: ...

        # Internally desugared this is equivalent to `foo`.
        def baz[M: MyProto](self: M) -> M: ...  # noqa: PYI019

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
    @no_type_check
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
            return "something"

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

    validate(main.compile())

def test_basic_parameterised(validate):
    @guppy.protocol
    class MyProto[T, S]:
        def foo(self: "MyProto[T, S]", x: T) -> S: ...

    @guppy.struct
    class MyType:
        @guppy
        def foo(self: "MyType", x: int) -> str:
            return "something"

    @guppy.struct
    class MyOtherType[P]:
        @guppy
        def foo(self: "MyType[P]", x: P) -> str:
            return "something"

    V = guppy.type_var("V")
    W = guppy.type_var("W")

    @guppy
    @no_type_check
    def baz1(a: MyProto[V, W], x: V) -> W:
        return a.foo(x)

    @guppy
    def baz2(a: MyProto[int, str]) -> str:
        return a.foo(42)

    @guppy
    def main() -> None:
        mt = MyType()
        baz1(mt, 42)
        baz2(mt)
        mot = MyOtherType[int]()
        baz1(mot, 42)
        baz2(mot)

    validate(main.compile())


def test_assumption(validate):
    @guppy.protocol
    class MyProto:
        def foo(self: "MyProto", x: int) -> str: ...

    @guppy
    def bar(a: MyProto) -> str:
        return a.foo(42)

    @guppy
    def main[P: MyProto](x: P) -> str:
        return bar(x)

    validate(main.compile_function())
