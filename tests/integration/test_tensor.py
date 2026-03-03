# ^ Stop ruff complaining about not knowing what "tensor" is

from collections.abc import Callable

from guppylang.decorator import guppy


def test_check_callable(validate):
    @guppy
    def bar(f: Callable[[int], bool]) -> Callable[[int], bool]:
        return f

    @guppy
    def foo(f: Callable[[int], bool]) -> tuple[Callable[[int], bool]]:
        return (f,)

    @guppy
    def is_42(x: int) -> bool:
        return x == 42

    @guppy
    def baz(x: int) -> bool:
        return foo(is_42)(x)

    @guppy
    def baz1() -> tuple[Callable[[int], bool]]:
        return foo(is_42)

    @guppy
    def baz2(x: int) -> bool:
        return (foo,)(is_42)(x)

    validate(baz.compile_function())
    validate(baz1.compile_function())
    validate(baz2.compile_function())


def test_call(validate):
    @guppy
    def foo() -> int:
        return 42

    @guppy
    def bar() -> bool:
        return True

    @guppy
    def baz_ho() -> tuple[Callable[[], int], Callable[[], bool]]:
        return (foo, bar)

    @guppy
    def baz_ho_id() -> tuple[Callable[[], int], Callable[[], bool]]:
        return baz_ho()

    @guppy
    def baz_ho_call() -> tuple[int, bool]:
        return baz_ho_id()()

    @guppy
    def baz() -> tuple[int, bool]:
        return (foo, bar)()

    @guppy
    def call_var() -> tuple[int, bool, int]:
        f = foo
        g = (foo, bar, f)
        return g()

    validate(baz_ho_call.compile_function())
    validate(baz.compile_function())
    validate(call_var.compile_function())


def test_call_inplace(validate):
    @guppy
    def local(f: Callable[[int], bool], g: Callable[[bool], int]) -> tuple[bool, int]:
        return (f, g)(42, True)

    validate(local.compile_function())


def test_singleton(validate):
    @guppy
    def foo(x: int, y: int) -> tuple[int, int]:
        return y, x

    @guppy
    def baz(x: int) -> tuple[int, int]:
        return (foo,)(x, x)

    validate(baz.compile_function())


def test_call_back(validate):
    @guppy
    def foo(x: int) -> int:
        return x

    @guppy
    def bar(x: int) -> int:
        return x * x

    @guppy
    def baz(x: int, y: int) -> tuple[int, int]:
        return (foo, bar)(x, y)

    @guppy
    def call_var(x: int) -> tuple[int, int, int]:
        f = foo, baz
        return f(x, x, x)

    validate(call_var.compile_function())


def test_normal(validate):
    @guppy
    def glo(x: int) -> int:
        return x

    @guppy
    def foo(x: int) -> int:
        return glo(x)

    validate(foo.compile_function())


def test_higher_order(validate):
    @guppy
    def foo(x: int) -> bool:
        return x > 42

    @guppy
    def bar(x: float) -> int:
        if x < 5.0:
            return 0
        else:
            return 1

    @guppy
    def baz() -> tuple[Callable[[int], bool], Callable[[float], int]]:
        return foo, bar

    # For the future:
    #
    #     @guppy
    #     def apply(f: Callable[[int, float],
    #               tuple[bool, int]],
    #               args: tuple[int, float]) -> tuple[bool, int]:
    #         return f(*args)
    #
    #     @guppy
    #     def apply_call(args: tuple[int, float]) -> tuple[bool, int]:
    #         return apply(baz, args)

    validate(baz.compile_function())


def test_nesting(validate):
    @guppy
    def foo(x: int, y: int) -> int:
        return x + y

    @guppy
    def bar(x: int) -> int:
        return -x

    @guppy
    def call(x: int) -> tuple[int, int, int]:
        f = bar, (bar, foo)
        return f(x, x, x, x)

    validate(call.compile_function())
