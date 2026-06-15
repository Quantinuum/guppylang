from guppylang.decorator import guppy
from guppylang.std.builtins import Fn
from tests.util import compile_guppy


def test_basic(validate):
    @guppy
    def bar(x: int) -> bool:
        return x > 0

    @guppy
    def foo() -> Fn[[int], bool]:
        return bar

    validate(foo.compile_function())


def test_call_1(validate):
    @guppy
    def bar() -> bool:
        return False

    @guppy
    def foo() -> Fn[[], bool]:
        return bar

    @guppy
    def baz() -> bool:
        return foo()()

    validate(baz.compile_function())


def test_call_2(validate):
    @guppy
    def bar(x: int) -> Fn[[int], None]:
        return bar(x - 1)

    @guppy
    def foo() -> Fn[[int], Fn[[int], None]]:
        return bar

    @guppy
    def baz(y: int) -> None:
        return foo()(y)(y)

    validate(baz.compile_function())


def test_conditional(validate):
    @guppy.declare
    def foo() -> int: ...

    @guppy.declare
    def bar() -> int: ...

    @guppy
    def main(b: bool) -> int:
        if b:
            baz = foo
        else:
            baz = bar
        return baz()

    validate(main.compile_function())


def test_method(validate):
    @guppy
    def foo(x: int) -> tuple[int, Fn[[int], int]]:
        f = x.__add__
        return f(1), f

    validate(foo.compile_function())


def test_nested(validate):
    @compile_guppy
    def foo(x: int) -> Fn[[int], bool]:
        def bar(y: int) -> bool:
            return x > y

        return bar

    validate(foo)


def test_nested_capture_struct(validate):
    @guppy.struct(frozen=True)
    class MyStruct:
        x: int

    @guppy
    def foo(s: MyStruct) -> Fn[[int], bool]:
        def bar(y: int) -> bool:
            return s.x > y

        return bar

    validate(foo.compile_function())


def test_nested_capture_enum(validate):
    @guppy.enum
    class MyEnum:
        VariantA = {}

        @guppy
        def tag(self) -> int:
            return 42

    @guppy
    def foo(e: MyEnum) -> Fn[[int], bool]:
        def bar(y: int) -> bool:
            return e.tag() > y

        return bar

    validate(foo.compile_function())


def test_curry(validate):
    @guppy
    def curry(f: Fn[[int, int], bool]) -> Fn[[int], Fn[[int], bool]]:
        def g(x: int) -> Fn[[int], bool]:
            def h(y: int) -> bool:
                return f(x, y)

            return h

        return g

    @guppy
    def uncurry(
        f: Fn[[int], Fn[[int], bool]],
    ) -> Fn[[int, int], bool]:
        def g(x: int, y: int) -> bool:
            return f(x)(y)

        return g

    @guppy
    def gt(x: int, y: int) -> bool:
        return x > y

    @guppy
    def main(x: int, y: int) -> None:
        curried = curry(gt)
        curried(x)(y)
        uncurried = uncurry(curried)
        uncurried(x, y)
        curry(uncurry(curry(gt)))(y)(x)

    validate(main.compile_function())


def test_y_combinator(validate):
    @guppy
    def fac_(f: Fn[[int], int], n: int) -> int:
        if n == 0:
            return 1
        return n * f(n - 1)

    @guppy
    def Y(f: Fn[[Fn[[int], int], int], int]) -> Fn[[int], int]:
        def y(x: int) -> int:
            return f(Y(f), x)

        return y

    @guppy
    def fac(x: int) -> int:
        return Y(fac_)(x)

    validate(fac.compile_function())
