from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.option import Option, nothing


def test_id(validate):
    T = guppy.type_var("T")

    @guppy
    def identity(x: T) -> T:
        return x

    validate(identity.compile_function())


def test_nonlinear(validate):
    T = guppy.type_var("T")

    @guppy
    def copy(x: T) -> tuple[T, T]:
        return x, x

    validate(copy.compile_function())


def test_apply(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy
    def apply(f: Callable[[S], T], x: S) -> T:
        return f(x)

    validate(apply.compile_function())


def test_annotate(validate):
    T = guppy.type_var("T")

    @guppy
    def identity(x: T) -> T:
        y: T = x
        return y

    validate(identity.compile_function())


def test_recurse(validate):
    T = guppy.type_var("T")

    @guppy
    def empty() -> T:
        return empty()

    validate(empty.compile_function())


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

    validate(foo.compile_function())


def test_nat_use(validate):
    n = guppy.nat_var("n")

    @guppy
    def foo(xs: array[int, n]) -> int:
        return int(n)

    validate(foo.compile_function())


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

    validate(empty.compile_function())


def test_type_apply(validate):
    T = guppy.type_var("T")
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(x: array[T, n]) -> array[T, n]: ...

    @guppy
    def identity(x: array[T, n]) -> array[T, n]:
        return foo[T, n](x)

    validate(identity.compile_function())


def test_custom_func_higher_order(validate):
    # See https://github.com/quantinuum/guppylang/issues/970
    T = guppy.type_var("T")

    @guppy
    def foo() -> Option[T]:
        f = nothing[T]
        return f()

    validate(foo.compile_function())
