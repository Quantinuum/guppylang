from guppylang import guppy
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            return y

        return bar(x + 1)

    validate(foo)


def test_call_twice(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            return y + 3

        if x > 5:
            return bar(x)
        else:
            return bar(2 * x)

    validate(foo)


def test_redefine(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            return y + 3

        a = bar(x)

        def bar(y: int) -> int:
            return y

        b = bar(0)
        return a + b

    validate(foo)


def test_define_twice(validate):
    @compile_guppy
    def foo(x: int) -> int:
        if x == 0:

            def bar(y: int) -> int:
                return y + 3
        else:

            def bar(y: int) -> int:
                return y - 42

        return bar(x)

    validate(foo)


def test_nested_deep(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            def baz(z: int) -> int:
                return z - 1

            return baz(5 * y)

        return bar(x + 1)

    validate(foo)


def test_recurse(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int) -> int:
            if y == 0:
                return 0
            return 2 * bar(y - 1)

        return bar(x)

    validate(foo)


def test_capture_arg(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar() -> int:
            return 1 + x

        return bar()

    validate(foo)


def test_capture_assigned(validate):
    @compile_guppy
    def foo(x: int) -> int:
        y = x + 1

        def bar() -> int:
            return y

        return bar()

    validate(foo)


def test_capture_multiple(validate):
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


def test_capture_fn(validate):
    @compile_guppy
    def foo() -> bool:
        def f(x: bool) -> bool:
            return x

        def g(b: bool) -> bool:
            return f(b)

        return g(True)

    validate(foo)


def test_capture_cfg(validate):
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


def test_capture_deep(validate):
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


def test_capture_recurse(validate):
    @compile_guppy
    def foo(x: int) -> int:
        def bar(y: int, z: int) -> int:
            if y == 0:
                return z
            return bar(z, z * x)

        return bar(x, 0)

    validate(foo)


def test_capture_recurse_nested(validate):
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


def test_capture_while(validate):
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
