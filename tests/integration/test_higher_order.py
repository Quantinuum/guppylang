from guppylang.decorator import guppy
from guppylang.std.builtins import Function
from tests.util import compile_guppy


def test_basic(validate):
    @guppy
    def bar(x: int) -> bool:
        return x > 0

    @guppy
    def foo() -> Function[[int], bool]:
        return bar

    validate(foo.compile_function())


def test_call_1(validate):
    @guppy
    def bar() -> bool:
        return False

    @guppy
    def foo() -> Function[[], bool]:
        return bar

    @guppy
    def baz() -> bool:
        return foo()()

    validate(baz.compile_function())


def test_call_2(validate):
    @guppy
    def bar(x: int) -> Function[[int], None]:
        return bar(x - 1)

    @guppy
    def foo() -> Function[[int], Function[[int], None]]:
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
            baz: Function[[], int] = foo
        else:
            baz: Function[[], int] = bar
        return baz()

    validate(main.compile_function())


def test_method(validate, use_experimental_features):
    @guppy
    def foo(x: int) -> tuple[int, Function[[int], int]]:
        f = x.__add__
        return f(1), f

    validate(foo.compile_function())


def test_nested(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> Function[[int], bool]:
        def bar(y: int) -> bool:
            return x > y

        return bar

    validate(foo)


def test_nested_capture_struct(validate, use_experimental_features):
    @guppy.struct(frozen=True)
    class MyStruct:
        x: int

    @guppy
    def foo(s: MyStruct) -> Function[[int], bool]:
        def bar(y: int) -> bool:
            return s.x > y

        return bar

    validate(foo.compile_function())


def test_nested_capture_enum(validate, use_experimental_features):
    @guppy.enum
    class MyEnum:
        VariantA = {}

        @guppy
        def tag(self) -> int:
            return 42

    @guppy
    def foo(e: MyEnum) -> Function[[int], bool]:
        def bar(y: int) -> bool:
            return e.tag() > y

        return bar

    validate(foo.compile_function())


def test_curry(validate, use_experimental_features):
    @guppy
    def curry(f: Function[[int, int], bool]) -> Function[[int], Function[[int], bool]]:
        def g(x: int) -> Function[[int], bool]:
            def h(y: int) -> bool:
                return f(x, y)

            return h

        return g

    @guppy
    def uncurry(
        f: Function[[int], Function[[int], bool]],
    ) -> Function[[int, int], bool]:
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


def test_y_combinator(validate, use_experimental_features):
    @guppy
    def fac_(f: Function[[int], int], n: int) -> int:
        if n == 0:
            return 1
        return n * f(n - 1)

    @guppy
    def Y(f: Function[[Function[[int], int], int], int]) -> Function[[int], int]:
        def y(x: int) -> int:
            return f(Y(f), x)

        return y

    @guppy
    def fac(x: int) -> int:
        return Y(fac_)(x)

    validate(fac.compile_function())
