from guppylang.decorator import guppy
from guppylang.std.builtins import nat, comptime, array


def test_basic_nat(validate):
    @guppy
    def foo(n: nat @ comptime) -> nat:
        return nat(n + 1)

    @guppy
    def main() -> nat:
        return foo(42)

    validate(main.compile_function())


def test_basic_int(validate):
    @guppy
    def foo(n: int @ comptime) -> int:
        return n + 1

    @guppy
    def main() -> int:
        return foo(42)

    validate(main.compile_function())


def test_basic_float(validate):
    @guppy
    def foo(f: float @ comptime) -> float:
        return f + 1.5

    @guppy
    def main() -> float:
        return foo(42.0)

    validate(main.compile_function())


def test_basic_bool(validate):
    @guppy
    def foo(b: bool @ comptime) -> bool:
        return not b

    @guppy
    def main() -> bool:
        return foo(True)

    validate(main.compile_function())


def test_multiple(validate):
    @guppy
    def foo(
        a: nat @ comptime, b: nat, c: nat @ comptime, d: nat, e: nat, f: nat @ comptime
    ) -> nat:
        return nat(a + b + c + d + e + f)

    @guppy
    def main() -> nat:
        return foo(1, 2, 3, 4, 5, 6)

    validate(main.compile_function())


def test_comptime_expr(validate):
    @guppy.declare
    def foo(n: nat @ comptime) -> nat: ...

    @guppy
    def main() -> nat:
        return foo(comptime(42 + 1))

    validate(main.compile_function())


def test_dependent(validate):
    @guppy
    def foo(n: nat @ comptime, xs: "array[int, n]") -> None:  # noqa: F821
        pass

    @guppy
    def main() -> None:
        foo(0, array())
        foo(1, array(1))
        foo(2, array(1, 2))

    validate(main.compile_function())


def test_dependent_generic(validate):
    x = guppy.nat_var("x")

    @guppy
    def foo(n: nat @ comptime, xs: "array[int, n]") -> None:  # noqa: F821
        pass

    @guppy
    def main(xs: array[int, x]) -> None:
        foo(x, xs)

    validate(main.compile_function())


def test_type_apply(validate):
    T = guppy.type_var("T")

    @guppy
    def foo(x: T, n: nat @ comptime) -> None:
        pass

    @guppy
    def main(m: nat @ comptime) -> None:
        foo[int, 43](42, 43)
        f = foo[float, 44]
        f(4.2, 44)
        g = foo[nat, m]
        g(42, m)

    validate(main.compile_function())


def test_generic1(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(_x: T, y: T @ comptime) -> T:
        return y

    @guppy
    def main(x: nat, y: int, z: float) -> float:
        return foo(x, 42) + foo(y, -10) + foo(z, 1.5)

    validate(main.compile_function())


def test_generic2(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(x: T @ comptime) -> T:
        return x

    @guppy
    def main() -> float:
        return foo(42) + foo(1.5)

    validate(main.compile_function())


def test_generic_tuple(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(t: tuple[T, T] @ comptime) -> T:
        x, _ = t
        return x

    @guppy
    def main() -> bool:
        return foo(comptime((True, False)))

    validate(main.compile_function())
