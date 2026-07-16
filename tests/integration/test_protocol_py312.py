import pytest
from typing import Self
from guppylang.decorator import guppy
from guppylang.std.builtins import nat
from guppylang.std.lang import Copy, Drop


def test_def():
    @guppy.protocol
    class MyProto:
        @guppy.require
        def foo(self: Self) -> "MyProto": ...

        # TODO: Implement Self support for protocols.
        @guppy.require
        def bar(self: Self) -> Self: ...

        # Internally desugared this is equivalent to `foo`.
        @guppy.require
        def baz[M: MyProto](self: M) -> M: ...  # noqa: PYI019

    MyProto.check()


def test_def_parameterised():
    @guppy.protocol
    class MyProto[T]:
        @guppy.require
        def foo(self: "MyProto[T]", x: T) -> T: ...

        # TODO: Implement Self support for protocols.
        # def bar(self: Self) -> "MyProto": ...

        @guppy.require
        def baz(self, y: int) -> int: ...

    MyProto.check()


def test_basic(validate):
    @guppy.protocol
    class MyProto:
        @guppy.require
        def foo(self, x: int) -> str: ...

    @guppy.struct(frozen=True)
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


def test_basic_parameterised_concrete(validate):
    from guppylang.std.builtins import owned

    @guppy.protocol
    class MyProto[T, S]:
        @guppy.require
        def foo(self: Self, x: T @ owned) -> S: ...

    @guppy.struct(frozen=True)
    class MyType:
        @guppy
        def foo(self: "MyType", x: int) -> str:
            return "something"

    @guppy
    def baz(a: MyProto[int, str]) -> str:
        return a.foo(42)

    @guppy
    def main() -> None:
        mt = MyType()
        baz(mt)

    validate(main.compile())


def test_basic_parameterised_generic(validate):
    @guppy.protocol
    class MyProto[T, S]:
        @guppy.require
        def foo(self, x: T) -> S: ...

    @guppy.struct(frozen=True)
    class MyType:
        @guppy
        def foo(self: "MyType", x: int) -> str:
            return "something"

    V = guppy.type_var("V")
    W = guppy.type_var("W")

    @guppy
    def baz(a: MyProto[V, W], x: V) -> W:
        return a.foo(x)

    @guppy
    def main() -> None:
        mt = MyType()
        baz(mt, 42)

    validate(main.compile())


def test_basic_parameterised_more_generic(validate):
    @guppy.protocol
    class MyProto:
        @guppy.require
        def foo(self, x: int) -> int: ...

    @guppy.struct(frozen=True)
    class MyType[T]:
        @guppy.declare
        def foo[T](self: "MyType[T]", x: T) -> T: ...

    @guppy
    def baz(a: MyProto, x: int) -> int:
        return a.foo(x)

    @guppy
    def main() -> None:
        mt = MyType[int]()
        baz(mt, 42)

    validate(main.compile())


def test_assumption(validate):
    @guppy.protocol
    class MyProto:
        @guppy.require
        def foo(self, x: int) -> str: ...

    @guppy
    def bar(a: MyProto) -> str:
        return a.foo(42)

    @guppy
    def baz[P: MyProto](x: P) -> str:
        return bar(x)

    @guppy.struct(frozen=True)
    class MyStruct:
        @guppy
        def foo(self, x: int) -> str:
            return ""

    @guppy
    def main() -> str:
        return baz(MyStruct())

    validate(main.compile())


@pytest.mark.skip
def test_self_inst(validate):
    @guppy.protocol
    class MyProto[T, S]:
        @guppy.require
        def foo(self: Self, t: T) -> S: ...

    @guppy.struct(frozen=True)
    class MyStruct:
        @guppy
        def foo(self: Self, t: int) -> str:
            return "4"

    @guppy
    def bar[A, B](p: MyProto[B, A], t: B) -> A:
        return p.foo(t)

    @guppy
    def main() -> str:
        return bar(MyStruct(), 42)

    validate(main.compile())


def test_multi(validate):
    from guppylang.std.builtins import nat, owned

    @guppy.protocol
    class Foo[T]:
        @guppy.require
        def foo(self: "Foo[T]", t: T @ owned) -> T: ...

    @guppy.protocol
    class Bar[T]:
        @guppy.require
        def bar(self: "Bar[T]", t: T @ owned) -> T: ...

    @guppy
    def baz[T: (Foo[nat], Bar[nat])](t: T) -> nat:
        return t.bar(t.foo(42))

    @guppy.struct(frozen=True)
    class MyStruct[T: (Copy, Drop)]:
        @guppy
        def foo(self, t: T) -> T:
            return t

        @guppy
        def bar(self, t: T) -> T:
            return t

    @guppy
    def main() -> nat:
        return baz(MyStruct[nat]())

    validate(main.compile())


@pytest.mark.skip
def test_nested(validate):
    from guppylang import guppy
    from guppylang.std.builtins import nat

    @guppy.protocol
    class NatId:
        @guppy.require
        def id(self: "NatId", x: nat) -> nat: ...

    @guppy.protocol
    class AnyId[T]:
        @guppy.require
        def id(self: Self, t: T) -> T: ...

    @guppy.struct(frozen=True)
    class Foo:
        @guppy
        def foo(self, x: nat) -> nat:
            return ""

    @guppy
    def eat_natid(p: NatId, n: nat) -> nat:
        return p.id(n)

    @guppy
    def eat_anyid[T](p: AnyId[T], n: T) -> T:
        return p.id(n)

    @guppy
    def bar(p: NatId, n: nat) -> nat:
        return eat_anyid(p, n)

    @guppy
    def main() -> str:
        return bar(Foo(), 42)

    validate(main.compile())


def test_specialise(validate):
    from guppylang import guppy
    from guppylang.std.builtins import nat

    @guppy.protocol
    class FooNat:
        @guppy.require
        def foo(self: "FooNat", n: nat) -> None: ...

    @guppy.protocol
    class FooStr:
        @guppy.require
        def foo(self: "FooStr", s: str) -> None: ...

    @guppy.struct(frozen=True)
    class Foo[T]:
        @guppy
        def foo(self, t: T) -> None:
            return None

    @guppy
    def eat_FooNat(f: FooNat) -> None:
        return f.foo(42)

    @guppy
    def eat_FooStr(f: FooStr) -> None:
        return f.foo("")

    @guppy
    def main() -> None:
        fn = Foo[nat]()
        eat_FooNat(fn)
        fs = Foo[str]()
        eat_FooStr(fs)
        return

    validate(main.compile())


def test_specialise2(validate):
    @guppy.protocol
    class FooNat:
        @guppy.require
        def foo(self: "FooNat", n: nat) -> None: ...

    @guppy.protocol
    class FooStr:
        @guppy.require
        def foo(self: "FooStr", s: str) -> None: ...

    @guppy.struct
    class Foo[T]:
        @guppy
        def foo(self, t: T) -> None:
            return None

    @guppy
    def bar[T](f: Foo[T], t: T) -> None:
        return f.foo(t)

    @guppy
    def main() -> None:
        bar(Foo[nat](), 42)
        bar(Foo[str](), "")

    validate(main.compile())


def test_run_int(validate, run_int_fn):
    @guppy.protocol
    class Animal:
        @guppy.require
        def fav_num(self: Self) -> nat: ...

    @guppy.struct(frozen=True)
    class Dog:
        @guppy
        def fav_num(self: Self) -> nat:
            return 4

    @guppy.struct(frozen=True)
    class Duck:
        @guppy
        def fav_num(self: Self) -> nat:
            return 9

    @guppy
    def sum_fav_num(a: Animal, b: Animal) -> nat:
        x = a.fav_num()
        x += b.fav_num()
        return x

    @guppy
    def main() -> nat:
        return sum_fav_num(Dog(), Duck())

    validate(main.compile())
    run_int_fn(main, 13)


def test_params(validate):
    @guppy.protocol
    class Foo[A, B]:
        @guppy.require
        def foo[C, D](self, a: A, c: C, d: D) -> B: ...

    @guppy.struct(frozen=True)
    class Goo:
        @guppy
        def foo[X, Y](self, n: nat, x: X, y: Y) -> float:
            return n * 2.5

    @guppy
    def hoo[F: Foo[nat, float]](f: F, n: nat, s: str, i: int) -> float:
        return f.foo(n, s, i)

    @guppy
    def main() -> float:
        return hoo(Goo(), 42, "", -1)

    validate(main.compile())


def test_clash(validate):
    @guppy.protocol
    class FooNat:
        @guppy.require
        def foo(self, n: nat) -> nat: ...

    @guppy.protocol
    class FooInt:
        @guppy.require
        def foo(self, n: int) -> int: ...

    @guppy.struct(frozen=True)
    class Foo:
        @guppy
        def foo[T: (Copy, Drop)](self, n: T) -> T:
            return n

    @guppy
    def bar_nat[T: (FooNat, FooInt)](t: T, n: nat) -> nat:
        return t.foo(n)

    @guppy
    def bar_int[T: (FooNat, FooInt)](t: T, n: int) -> int:
        return t.foo(n)

    @guppy
    def main() -> None:
        bar_nat(Foo(), 42)
        bar_int(Foo(), 42)
        return

    validate(main.compile())


def test_unitary(validate):
    from guppylang import guppy
    from guppylang.std.builtins import (
        Unitary,
        control,
        dagger,
    )
    from guppylang.std.quantum import discard, h, qubit, s

    @guppy(unitary=True)
    def apply(f: Unitary[[qubit], None], q: qubit) -> None:
        apply2(f, q)

    @guppy(unitary=True)
    def apply2(f: Unitary[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def main() -> None:
        q = qubit()
        c = qubit()
        h(c)
        with control(c), dagger:
            apply(s, q)
            apply(h, q)
        discard(q)
        discard(c)

    validate(main.compile())


def test_double_fn(validate):
    from collections.abc import Callable
    from guppylang.std.builtins import qubit

    @guppy
    def take_two(
        a: Callable[[qubit], None], b: Callable[[qubit], None], q: qubit
    ) -> None:
        a(q)
        b(q)

    @guppy
    def fn(q: qubit) -> None:
        return

    @guppy
    def fn2(q: qubit) -> None:
        return

    @guppy
    def call_two() -> None:
        q = qubit()
        take_two(fn, fn2, q)
        take_two(fn, fn, q)
        q.discard()

    validate(call_two.compile())


def test_comptime(validate, run_int_fn):
    @guppy.protocol
    class Animal[T]:
        @guppy.require
        def fav_num(self: Self, x: T) -> int: ...

    @guppy.struct(frozen=True)
    class Dog:
        @guppy.comptime
        def fav_num(self: Self, n: nat) -> int:
            return n + 1

    @guppy.struct(frozen=True)
    class Duck:
        @guppy.comptime
        def fav_num(self: Self, x: int) -> int:
            return x + 2

    V = guppy.type_var("V")
    W = guppy.type_var("W")

    @guppy.comptime
    def sum_fav_num(a: Animal[V], b: Animal[W], x: V, y: W) -> int:
        return a.fav_num(x) + b.fav_num(y)

    @guppy.comptime
    def main() -> int:
        return sum_fav_num(Dog(), Duck(), nat(1), 2)

    validate(main.compile())
    run_int_fn(main, 6)
