from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.lang import Function
from guppylang import qubit
from guppylang.std.builtins import owned
from guppylang.std.quantum import measure


def test_function_is_callable(validate):
    @guppy
    def bar(x: int) -> bool:
        return x > 0

    @guppy
    def baz(x: int) -> bool:
        return x < 0

    @guppy
    def foo(f: Callable[[int], bool]) -> bool:
        return f(42)

    # foo on its own can't be compiled, but we can check it
    foo.check()

    @guppy
    def main() -> bool:
        g = baz
        return foo(bar) or foo(g)

    validate(main.compile_function())


def test_callable_is_callable(validate):
    @guppy
    def foo(f: Callable[[], None]) -> None:
        foo(f)

    @guppy
    def main() -> None:
        def bar() -> None:
            pass

        foo(bar)

    validate(main.compile_function())


def test_generic(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def foo1(f: Callable[[T], T]) -> None: ...

    @guppy.declare
    def foo2(f: Callable[[S], int]) -> None: ...

    @guppy.declare
    def bar1(x: int) -> int: ...

    @guppy.declare
    def bar2(x: bool) -> T: ...

    @guppy
    def main() -> None:
        foo1[int, Function[[int], int]](bar1)
        foo2[bool, Function[[bool], int]](bar2[int])

        # Everything can be inferred:
        foo1(bar1)
        foo2[bool, Function[[bool], int]](bar2)
        foo2(bar2[int])
        foo2(bar2)

    validate(main.compile_function())


def test_return_rows(validate):
    T = guppy.type_var("T")

    @guppy
    def call(f: Callable[[], T]) -> T:
        return f()

    @guppy
    def return_none() -> None:
        pass

    @guppy
    def return_single() -> int:
        return 42

    @guppy
    def return_tuple() -> tuple[bool, int, float]:
        return False, 42, 1.5

    @guppy
    def main() -> float:
        call(return_none)
        x = call(return_single)
        a, b, c = call(return_tuple)
        return x + c if a else b + c

    validate(main.compile_function())


def test_nested(validate):
    @guppy
    def call(f: Callable[[int, int], int]) -> int:
        return f(1, 2)

    @guppy
    def main() -> int:
        @guppy
        def add(x: int, y: int) -> int:
            return x + y

        @guppy
        def sub(x: int, y: int) -> int:
            return x - y

        return call(add) + call(sub)

    validate(main.compile_function())


def test_dunder_callable(validate):
    @guppy.struct(frozen=True)
    class Counter:
        value: int

        @guppy
        def __call__(self, increment: int) -> int:
            return self.value + increment

    @guppy
    def twice(f: Callable[[int], int]) -> int:
        first = f(2)
        return first + f(3)

    @guppy
    def main() -> int:
        counter = Counter(10)
        inferred = counter(1)
        checked: int = counter(1)
        return inferred + checked + twice(counter) + counter.value

    validate(main.compile())


def test_dunder_callable_return_rows(validate):
    @guppy.struct(frozen=True)
    class NoResult:
        @guppy
        def __call__(self) -> None:
            pass

    @guppy.struct(frozen=True)
    class Pair:
        value: int

        @guppy
        def __call__(self) -> tuple[int, bool]:
            return self.value, True

    @guppy
    def call_none(f: Callable[[], None]) -> None:
        f()

    @guppy
    def call_pair(f: Callable[[], tuple[int, bool]]) -> tuple[int, bool]:
        return f()

    @guppy
    def main() -> int:
        call_none(NoResult())
        value, flag = call_pair(Pair(42))
        return value if flag else 0

    validate(main.compile())


def test_dunder_callable_owned(validate):
    @guppy.struct(frozen=True)
    class Measure:
        @guppy
        def __call__(self, q: qubit @ owned) -> bool:
            return bool(measure(q))

    @guppy
    def apply(f: Callable[[qubit @ owned], bool], q: qubit @ owned) -> bool:
        return f(q)

    @guppy
    def main() -> bool:
        return apply(Measure(), qubit())

    validate(main.compile())
