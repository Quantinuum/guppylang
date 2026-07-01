from typing import Generic

import pytest

from hugr import tys as ht

from hugr import Wire

from guppylang.decorator import guppy
from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang.std.builtins import array, Function, comptime, Copy, Drop, nat, owned
from guppylang.std.option import Option, nothing
from guppylang.std.quantum import qubit


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
    def foo(f: Function[[T], T]) -> None: ...

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
    def foo(f: Function[[S], int]) -> None: ...

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
    def foo(f: Function[[T], T]) -> None: ...

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
        f: Function[[int], int] = foo
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


def test_function(validate):
    @guppy
    def foo[S, T](x: S @ owned, y: T @ owned) -> tuple[T, S]:
        return y, x

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> None:
        foo(1, 2)
        foo(True, False)

    validate(main.compile_function())


def test_struct(validate):
    @guppy.struct
    class MyStruct[S, T]:
        x: S
        y: T

    @guppy
    def main(s: MyStruct[int, float]) -> float:
        return s.x + s.y

    validate(main.compile_function())


def test_enum(validate):
    @guppy.enum
    class MyEnum[S, T]:
        VariantA = {"x": S}
        VariantB = {"x": S, "y": T}

    @guppy
    def main() -> None:
        MyEnum.VariantA[int, float](1)
        MyEnum.VariantB[int, float](2, 3.0)

    validate(main.compile_function())


def test_inner_frame(validate):
    """See https://github.com/quantinuum/guppylang/issues/1116"""

    def make():
        @guppy.struct
        class MyStruct[T]:
            @guppy
            def foo(self: "MyStruct[int]") -> None:
                pass

        @guppy.enum
        class MyEnum[T]:
            VariantA = {}

            @guppy
            def method(self: "MyEnum[int]") -> None:
                pass

        @guppy
        def main() -> None:
            MyStruct[int]().foo()
            MyEnum.VariantA[int]().method()

        return main

    validate(make().compile_function())


def test_copy_bound(validate):

    @guppy.struct
    class MyStruct[T: Copy]:
        x: T

    @guppy.enum
    class MyEnum[T: Copy]:
        VariantA = {"x": T}

    @guppy
    def foo_enum[T: Copy](e1: MyEnum[T]) -> tuple[MyEnum[T], MyEnum[T]]:
        return e1, e1

    @guppy
    def foo_struct[T: Copy](s: MyStruct[T]) -> tuple[T, T]:
        return s.x, s.x

    # We can't compile the functions on their own, but we can check them
    foo_enum.check()
    foo_struct.check()

    @guppy
    def main() -> None:
        foo_struct(MyStruct(42))
        foo_struct(MyStruct(False))
        foo_enum(MyEnum.VariantA[int](42))
        foo_enum(MyEnum.VariantA[bool](False))

    validate(main.compile_function())


def test_drop_bound(validate):
    @guppy.struct
    class MyStruct[T: Drop]:
        x: T

    @guppy.enum
    class MyEnum[T: Drop]:
        VariantA = {"x": T}

    @guppy
    def helper[T: Drop](s: MyStruct[T] @ owned, e: MyEnum[T] @ owned) -> None:
        pass

    # We can't compile helper on its own, but we can check it
    helper.check()

    @guppy
    def main(
        s: MyStruct[array[int, 5]] @ owned, e: MyEnum[array[int, 5]] @ owned
    ) -> None:
        helper(s, e)

    helper.check()
    validate(main.compile_function())


def test_copy_and_drop_bound(validate):
    @guppy.struct
    class MyStruct[T: (Copy, Drop)]:
        x: T

    @guppy.enum
    class MyEnum[T: (Copy, Drop)]:
        VariantA = {"x": T}

    @guppy
    def foo[T: (Copy, Drop)](
        s1: MyStruct[T], s2: MyStruct[T], e1: MyEnum[T], e2: MyEnum[T]
    ) -> tuple[T, T, MyEnum[T], MyEnum[T]]:
        return s1.x, s1.x, e1, e1

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> None:
        foo(
            MyStruct(42),
            MyStruct(43),
            MyEnum.VariantA[int](42),
            MyEnum.VariantA[int](43),
        )
        foo(
            MyStruct(False),
            MyStruct(True),
            MyEnum.VariantA[bool](False),
            MyEnum.VariantA[bool](True),
        )

    validate(main.compile_function())


def test_const_param(validate):
    @guppy.struct
    class MyStruct[T, n: nat]:
        xs: array[T, n]

    @guppy.enum
    class MyEnum[T, n: nat]:
        VariantA = {"xs": array[T, n]}
        VariantB = {}

    @guppy
    def foo[T, n: nat](xs: array[T, n], s: MyStruct[T, n], e: MyEnum[T, n]) -> nat:
        return n

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> None:
        foo(array(1, 2, 3), MyStruct(array(4, 5, 6)), MyEnum.VariantA(array(7, 8, 9)))
        foo[float, 0](array(), MyStruct(array()), MyEnum.VariantB[float, 0]())

    validate(main.compile_function())


def test_mixed_legacy_params(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy
    def foo[S](x: S @ owned, y: T @ owned) -> tuple[T, S]:
        return y, x

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> tuple[qubit, qubit]:
        foo(1, 2)
        return foo(qubit(), qubit())

    validate(main.compile_function())


def test_reference_inside(validate):
    @guppy
    def helper[T: Drop]() -> None:
        x: Option[T] = nothing()
        nothing[T]()

    # We can't compile helper on its own, but we can check it
    helper.check()

    # Just check we can instantiate a Drop type-parameter with a classical type.
    @guppy
    def main() -> None:
        helper[int]()

    validate(main.compile_function())


def test_dependent_function(validate):
    @guppy
    def foo[T: (Copy, Drop), x: T]() -> T:
        return x

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> float:
        return foo[nat, 42]() + foo[float, 1.5]()

    validate(main.compile_function())


@guppy.struct
class Phantom[T: (Copy, Drop), x: T]:
    """Dummy struct with dependent parameters."""

    @guppy
    def get[T: (Copy, Drop), x: T](self: "Phantom[T, x]") -> T:
        return x


def test_dependent_struct(run_float_fn_approx):
    @guppy
    def make_phantom[T: (Copy, Drop)](x: T @ comptime) -> "Phantom[T, x]":  # noqa: F821
        return Phantom()

    @guppy
    def foo(x: Phantom[bool, True]) -> float:
        return 0.0 if x.get() else make_phantom(42).get() + make_phantom(1.5).get()

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> float:
        return foo(Phantom())

    run_float_fn_approx(main, 0)


def test_dependent_comptime(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(x: T @ comptime, y: "Phantom[T, x]") -> T:  # noqa: F821
        return y.get()

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> int:
        return foo(42, Phantom())

    validate(main.compile_function())


def test_multi_dependent():
    @guppy
    def foo[
        T: (Copy, Drop),
        x: T,
        y: Phantom[T, x],
        z: Phantom[Phantom[T, x], y],
    ]() -> tuple[T, T, T]:
        return x, y.get(), z.get().get()

    # We can't define a main that calls `foo` since we don't have comptime constructors
    # for structs yet. We can't even check that `foo` type checks


def test_generic_tuple_chain(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def bar(t: tuple[T, T] @ comptime, p: "Phantom[tuple[T, T], t]") -> T:  # noqa: F821
        return p.get()[0]

    @guppy
    def foo(a: tuple[T, T] @ comptime) -> T:
        return bar(a, Phantom())

    # We can't compile foo on its own, but we can check it
    foo.check()

    @guppy
    def main() -> int:
        return foo(comptime((1, 2)))

    validate(main.compile_function())
