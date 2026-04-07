from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.option import Option, nothing


def build_main(f) -> None:
    @guppy
    def main() -> None:
        f(True)
        f(42)
        f((1.5, False))
        f(None)

    return main


def build_array_main(f) -> None:
    @guppy
    def main(xs: array[float, 0] @ owned) -> None:
        f(array(True, False))
        f(array((1, 2), (3, 4), (5, 6)))
        f(array(None))
        f(xs)

    return main


def test_id(validate):
    T = guppy.type_var("T")

    @guppy
    def identity(x: T) -> T:
        return x

    validate(build_main(identity).compile_function())


def test_nonlinear(validate):
    T = guppy.type_var("T")

    @guppy
    def copy(x: T) -> tuple[T, T]:
        return x, x

    validate(build_main(copy).compile_function())


def test_apply(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy
    def apply(f: Callable[[S], T], x: S) -> T:
        return f(x)

    @guppy
    def foo(x: int) -> tuple[int, int]:
        return x, x

    @guppy
    def bar(x: int) -> None:
        pass

    @guppy
    def baz(x: tuple[int, int]) -> float:
        a, b = x
        return a + b + 1.5

    @guppy
    def main() -> float:
        x = apply(foo, 42)
        apply(bar, x[0])
        return apply(baz, x)

    validate(main.compile_function())


def test_annotate(validate):
    T = guppy.type_var("T")

    @guppy
    def identity(x: T) -> T:
        y: T = x
        return y

    validate(build_main(identity).compile_function())


def test_recurse(validate):
    T = guppy.type_var("T")

    @guppy
    def empty() -> T:
        return empty()

    @guppy
    def main() -> None:
        x: int = empty()
        y: tuple[int, float] = empty()
        z: None = empty()

    validate(main.compile_function())


def test_call(validate):
    T = guppy.type_var("T")

    @guppy
    def identity(x: T) -> T:
        return x

    @guppy
    def main() -> float:
        return identity(5) + identity(42.0)

    validate(main.compile_function())


def test_nat(validate):
    T = guppy.type_var("T")
    n = guppy.nat_var("n")

    @guppy
    def foo(xs: array[T, n] @ owned) -> array[T, n]:
        return xs

    validate(build_array_main(foo).compile_function())


def test_nat_use(validate):
    n = guppy.nat_var("n")

    @guppy
    def foo(xs: array[int, n]) -> int:
        return int(n)

    @guppy
    def main(xs: array[int, 0]) -> None:
        foo(array(0))
        foo(array(0, 1, 2))
        foo(xs)

    validate(main.compile_function())


def test_nat_call(validate):
    T = guppy.type_var("T")
    n = guppy.nat_var("n")

    @guppy
    def foo() -> array[T, n]:
        return foo()

    @guppy
    def main() -> tuple[array[int, 10], array[float, 20]]:
        return foo(), foo()

    validate(main.compile_function())


def test_nat_recurse(validate):
    n = guppy.nat_var("n")

    @guppy
    def empty() -> array[int, n]:
        return empty()

    @guppy
    def main() -> None:
        x: array[int, 42] = empty()
        y: array[int, 0] = empty()

    validate(main.compile_function())


def test_type_apply(validate):
    T = guppy.type_var("T")
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(x: array[T, n]) -> array[T, n]: ...

    @guppy
    def identity(x: array[T, n]) -> array[T, n]:
        return foo[T, n](x)

    validate(build_array_main(identity).compile_function())


def test_custom_func_higher_order(validate):
    # See https://github.com/quantinuum/guppylang/issues/970
    T = guppy.type_var("T")

    @guppy
    def foo() -> Option[T]:
        f = nothing[T]
        return f()

    @guppy
    def main() -> None:
        x: Option[int] = foo()
        y: Option[tuple[int, float]] = foo()
        z: Option[None] = foo()

    validate(main.compile_function())
