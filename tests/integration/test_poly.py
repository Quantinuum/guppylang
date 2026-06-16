from collections.abc import Callable
from typing import Generic

import pytest

from hugr import tys as ht

from hugr import Wire

from guppylang.decorator import guppy
from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang.std.builtins import array
from guppylang.std.quantum import discard, h, qubit


def test_id(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(x: int) -> int:
        return foo(x)

    validate(main.compile_function())


def test_id_nested(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(x: int) -> int:
        return foo(foo(foo(x)))

    validate(main.compile_function())


def test_use_twice(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(x: int, y: bool) -> None:
        foo(x)
        foo(y)

    validate(main.compile_function())


def test_generic_functions_in_unitary_class(validate):
    @guppy.unitary
    class foo:
        T = guppy.type_var("T")

        @guppy
        def identity(x: T) -> T:
            return x

        @guppy
        def helper(q: qubit, n: int) -> int:
            h(q)
            return identity(n)  # noqa: F821

        @guppy
        def __call__(q: qubit) -> None:
            n = identity(1)  # noqa: F821
            helper(q, n)  # noqa: F821

        @guppy
        def call_daggered(q: qubit) -> None:
            n = identity(2)  # noqa: F821
            helper(q, n)  # noqa: F821

        # TODO: make the _controls argument generic
        @guppy
        def call_controlled(q: qubit, _controls: array[qubit, 1]) -> None:
            n = identity(3)  # noqa: F821
            helper(q, n)  # noqa: F821
            helper(_controls[0], identity(n))  # noqa: F821

        @guppy
        def call_ctrl_daggered(q: qubit, _controls: array[qubit, 1]) -> None:
            n = identity(4)  # noqa: F821
            helper(q, n)  # noqa: F821
            helper(_controls[0], identity(n))  # noqa: F821

    @guppy
    def main() -> None:
        q = qubit()
        foo(q)
        discard(q)

    validate(main.compile())


def test_define_twice(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy.declare
    def bar(x: T) -> T:  # Reuse same type var!
        ...

    @guppy
    def main(x: bool, y: float) -> None:
        foo(x)
        foo(y)

    validate(main.compile_function())


def test_return_tuple_implicit(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(x: int) -> tuple[int, int]:
        return foo((x, 0))

    validate(main.compile_function())


def test_same_args(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T, y: T) -> None: ...

    @guppy
    def main(x: int) -> None:
        foo(x, 42)

    validate(main.compile_function())


def test_different_args(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: S, y: T, z: tuple[S, T]) -> T: ...

    @guppy
    def main(x: int, y: float) -> float:
        return foo(x, y, (x, y)) + foo(y, 42.0, (0.0, y))

    validate(main.compile_function())


def test_nat_args(validate):
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(x: array[int, n]) -> array[int, n]: ...

    @guppy
    def main(x: array[int, 42]) -> array[int, 42]:
        return foo(x)

    validate(main.compile_function())


def test_infer_basic(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo() -> T: ...

    @guppy
    def main() -> None:
        x: int = foo()

    validate(main.compile_function())


def test_infer_list(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo() -> T: ...

    @guppy
    def main() -> None:
        xs: list[int] = [foo()]
        ys = [1.0, foo()]

    validate(main.compile_function())


def test_infer_nested(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo() -> T: ...

    @guppy.declare
    def bar(x: T) -> T: ...

    @guppy
    def main() -> None:
        x: int = bar(foo())

    validate(main.compile_function())


def test_infer_left_to_right(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def foo() -> T: ...

    @guppy.declare
    def bar(x: T, y: T, z: S, a: tuple[T, S]) -> None: ...

    @guppy
    def main() -> None:
        bar(42, foo(), False, foo())

    validate(main.compile_function())


def test_type_apply_basic(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy.declare
    def bar(x: S, y: T) -> S: ...

    @guppy
    def main() -> tuple[int, float, float]:
        x = foo[int](0)
        y = foo[float](1.0)
        z = bar[float, int](y, x)
        return x, y, z

    validate(main.compile_function())


def test_type_apply_higher_order(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy.declare
    def bar(x: S, y: T) -> S: ...

    @guppy
    def main() -> tuple[int, float, float]:
        f = foo[int]
        g = foo[float]
        h = bar[float, int]
        x = f(0)
        y = g(1.0)
        z = h(y, x)
        return x, y, z

    validate(main.compile_function())


def test_type_apply_nat(validate):
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(x: array[int, n]) -> int: ...

    @guppy
    def main() -> int:
        return foo[0](array()) + foo[2](array(1, 2))

    validate(main.compile_function())


def test_type_apply_empty_tuple(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> None: ...

    @guppy
    def main() -> None:
        # `()` is the type of an empty tuple (`tuple[]` is not syntactically valid)
        foo[()]

    validate(main.compile_function())


def test_type_apply_empty_array(validate):
    T = guppy.type_var("T")
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(xs: array[T, n]) -> array[T, n]: ...

    @guppy
    def main() -> None:
        xs: array[float, 0] = foo(array())

    validate(main.compile_function())


def test_type_apply_method(validate):
    T = guppy.type_var("T")

    @guppy.struct
    class MyStruct(Generic[T]):
        @guppy
        def foo(self: "MyStruct[T]") -> None:
            pass

    @guppy.enum
    class MyEnum(Generic[T]):
        VariantA = {}

        @guppy
        def method(self: "MyEnum[T]") -> None:
            pass

    @guppy
    def main(s: MyStruct[int], e: MyEnum[int]) -> None:
        s.foo[int]()
        e.method[int]()

    validate(main.compile_function())


def test_pass_poly_basic(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(f: Callable[[T], T]) -> None: ...

    @guppy.declare
    def bar(x: int) -> int: ...

    @guppy
    def main() -> None:
        foo(bar)

    validate(main.compile_function())


def test_pass_poly_cross(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def foo(f: Callable[[S], int]) -> None: ...

    @guppy.declare
    def bar(x: bool) -> T: ...

    @guppy
    def main() -> None:
        foo(bar)

    validate(main.compile_function())


def test_linear(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(q: qubit) -> qubit:
        return foo(q)

    validate(main.compile_function())


def test_affine(validate):
    T = guppy.type_var("T", copyable=False, droppable=True)

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(a: array[int, 7]) -> None:
        foo(a)

    validate(main.compile_function())


def test_relevant(validate):
    T = guppy.type_var("T", copyable=True, droppable=False)

    @custom_type(ht.Bool, copyable=True, droppable=False)
    class R: ...

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(r: R) -> R:
        r_copy = r
        return foo(r_copy)

    validate(main.compile_function())


def test_pass_nonlinear(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy
    def main(x: int) -> None:
        foo(x)

    validate(main.compile_function())


def test_pass_linear(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy.declare
    def foo(f: Callable[[T], T]) -> None: ...

    @guppy.declare
    def bar(q: qubit) -> qubit: ...

    @guppy
    def main() -> None:
        foo(bar)

    validate(main.compile_function())


def test_custom_higher_order():
    class CustomCompiler(CustomCallCompiler):
        def compile(self, args: list[Wire]) -> list[Wire]:
            return args

    T = guppy.type_var("T")

    @custom_function(CustomCompiler())
    def foo(x: T) -> T: ...

    @guppy
    def main(x: int) -> int:
        f: Callable[[int], int] = foo
        return f(x)


@pytest.mark.skip("Higher-order polymorphic functions are not yet supported")
def test_higher_order_value(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def foo(x: T) -> T: ...

    @guppy.declare
    def bar(x: T) -> T: ...

    @guppy
    def main(b: bool) -> int:
        f = foo if b else bar
        return f(42)

    validate(main.compile_function())
