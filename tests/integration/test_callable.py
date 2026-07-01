from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.lang import Function


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


def test_struct(validate):
    @guppy.struct
    class MyStruct[F: Callable[[int], int]]:
        f: F

        @guppy
        def call(self) -> int:
            return self.f(42)

    @guppy.declare
    def foo(x: int) -> int: ...

    @guppy.declare
    def bar[T](x: T) -> int: ...

    @guppy.declare
    def baz[T](x: int) -> T: ...

    @guppy
    def main() -> int:
        return MyStruct(foo).call() + MyStruct(bar).call() + MyStruct(baz).call()

    validate(main.compile_function())


def test_struct_generic(validate):
    @guppy.struct
    class MyStruct[S, T, F: Callable[[S], T]]:
        f: F
        x: S

        @guppy
        def call(self) -> T:
            return self.f(self.x)

    @guppy.declare
    def foo(x: int) -> int: ...

    @guppy.declare
    def bar[U](x: U) -> int: ...

    @guppy
    def main() -> int:
        return MyStruct(foo, 42).call() + MyStruct(bar[bool], False).call()

    validate(main.compile_function())
