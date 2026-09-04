from guppylang import guppy
from tests.util import compile_guppy


def test_basic(run_int_fn):
    @guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            return y * 2

        return bar(x + 1)

    run_int_fn(foo, expected=12, args=[5])


def test_call_twice(run_int_fn):
    @guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            return y + 3

        if x > 5:
            return bar(x)
        else:
            return bar(2 * x)

    run_int_fn(foo, expected=13, args=[5])
    run_int_fn(foo, expected=9, args=[6])


def test_redefine(run_int_fn):
    @guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            return y + 3

        a = bar(x)

        def bar(y: int) -> int:
            return y

        b = bar(0)
        return a + b

    run_int_fn(foo, expected=5, args=[2])


def test_define_twice(run_int_fn):
    from guppylang.std.builtins import Function  # noqa: TC002

    @guppy
    def foo(x: int) -> int:
        if x == 0:

            def bar(y: int) -> int:
                return y + 3

            bar: Function[[int], int] = bar
        else:

            def bar(y: int) -> int:
                return y - 42

            bar: Function[[int], int] = bar

        return bar(x)

    run_int_fn(foo, expected=3, args=[0])
    run_int_fn(foo, expected=1, args=[43])


def test_nested_deep(run_int_fn):
    @guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            def baz(z: int) -> int:
                return z - 1

            return baz(5 * y)

        return bar(x + 1)

    run_int_fn(foo, expected=29, args=[5])


def test_recurse(run_int_fn):
    @guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            if y == 0:
                return 1
            return 2 * bar(y - 1)

        return bar(x)

    run_int_fn(foo, expected=32, args=[5])


def test_capture_arg(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        def bar() -> int:
            return 1 + x

        return bar()

    validate(foo)


def test_capture_assigned(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        y = x + 1

        def bar() -> int:
            return y

        return bar()

    validate(foo)


def test_capture_multiple(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        if x > 5:
            y = 3
        else:
            y = 2 * x
        z = x + y

        def bar() -> int:
            q = y
            return q + z

        return bar()

    validate(foo)


def test_capture_fn(validate, use_experimental_features):
    @compile_guppy
    def foo() -> bool:
        def f(x: bool) -> bool:
            return x

        def g(b: bool) -> bool:
            return f(b)

        return g(True)

    validate(foo)


def test_capture_cfg(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        a = x + 4
        if x > 5:
            y = 5

            def bar() -> int:
                return x + y + a

            return bar()
        return 4

    validate(foo)


def test_capture_deep(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        a = x * 2

        def bar() -> int:
            b = a + 1

            def baz(y: int) -> int:
                c = a + b + y + x
                return c

            return baz(b * a)

        return bar()

    validate(foo)


def test_capture_recurse(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int, z: int) -> int:
            if y == 0:
                return z
            return bar(z, z * x)

        return bar(x, 0)

    validate(foo)


def test_capture_recurse_nested(validate, use_experimental_features):
    @guppy
    def foo(x: int) -> int:
        def bar(y: int, z: int) -> int:
            if y == 0:
                return z

            def baz() -> int:
                if z < 42:
                    return bar(z, z * x)
                return foo(z - 2)

            return baz()

        return bar(x, 0)

    validate(foo.compile_function())


def test_capture_while(validate, use_experimental_features):
    @compile_guppy
    def foo(x: int) -> int:
        a = 0
        while x > 0:

            def bar() -> int:
                return x * x

            a += bar()
            x -= 1
        return a

    validate(foo)
