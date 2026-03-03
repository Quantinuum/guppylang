"""Tests Python 3.12 style generic syntax."""

from guppylang import array
from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop, owned, comptime
from guppylang.std.num import nat
from guppylang.std.option import Option, nothing


def test_function(validate):
    @guppy
    def main[S, T](x: S @ owned, y: T @ owned) -> tuple[T, S]:
        return y, x

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


def test_inner_frame(validate):
    """See https://github.com/quantinuum/guppylang/issues/1116"""

    def make():
        @guppy.struct
        class MyStruct[T]:
            @guppy
            def foo(self: "MyStruct[int]") -> None:
                pass

        @guppy
        def main() -> None:
            MyStruct[int]().foo()

        return main

    validate(make().compile_function())


def test_copy_bound(validate):
    @guppy.struct
    class MyStruct[T: Copy]:
        x: T

    @guppy
    def main[T: Copy](s: MyStruct[T]) -> tuple[T, T]:
        return s.x, s.x

    validate(main.compile_function())


def test_drop_bound(validate):
    @guppy.struct
    class MyStruct[T: Drop]:
        x: T

    @guppy
    def helper[T: Drop](s: MyStruct[T] @ owned) -> None:
        pass

    @guppy
    def main(s: MyStruct[array[int, 5]] @ owned) -> None:
        helper(s)

    validate(main.compile_function())


def test_copy_and_drop_bound(validate):
    @guppy.struct
    class MyStruct[T: (Copy, Drop)]:
        x: T

    @guppy
    def main[T: (Copy, Drop)](s1: MyStruct[T], s2: MyStruct[T]) -> tuple[T, T]:
        return s1.x, s1.x

    validate(main.compile_function())


def test_const_param(validate):
    @guppy.struct
    class MyStruct[T, n: nat]:
        xs: array[T, n]

    @guppy
    def main[T, n: nat](xs: array[T, n], s: MyStruct[T, n]) -> nat:
        return n

    validate(main.compile_function())


def test_mixed_legacy_params(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy
    def main[S](x: S @ owned, y: T @ owned) -> tuple[T, S]:
        return y, x

    validate(main.compile_function())


def test_reference_inside(validate):
    @guppy
    def helper[T: Drop]() -> None:
        x: Option[T] = nothing()
        nothing[T]()

    # Just check we can instantiate a Drop type-parameter with a classical type.
    @guppy
    def main() -> None:
        helper[int]()

    validate(main.compile_function())


def test_dependent_function(validate):
    @guppy
    def foo[T: (Copy, Drop), x: T]() -> T:
        return x

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

    @guppy
    def main() -> float:
        return foo(Phantom())

    run_float_fn_approx(main, 0)


def test_dependent_comptime(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(x: T @ comptime, y: "Phantom[T, x]") -> T:  # noqa: F821
        return y.get()

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
    # for structs yet. We can check that `foo` type checks though
    foo.check()


def test_generic_tuple_chain(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def bar(t: tuple[T, T] @ comptime, p: "Phantom[tuple[T, T], t]") -> T:  # noqa: F821
        return p.get()[0]

    @guppy
    def foo(a: tuple[T, T] @ comptime) -> T:
        return bar(a, Phantom())

    @guppy
    def main() -> int:
        return foo(comptime((1, 2)))

    validate(main.compile_function())
