from typing import Generic, TYPE_CHECKING

from guppylang.decorator import guppy


if TYPE_CHECKING:
    from collections.abc import Callable


def test_basic_defs(validate):
    @guppy.struct
    class EmptyStruct:
        pass

    @guppy.struct
    class OneMemberStruct:
        x: int

    @guppy.struct
    class TwoMemberStruct:
        x: tuple[bool, int]
        y: float

    @guppy.struct
    class DocstringStruct:
        """This is struct with a docstring!"""

        x: int

    @guppy
    def main(
        a: EmptyStruct, b: OneMemberStruct, c: TwoMemberStruct, d: DocstringStruct
    ) -> None:
        EmptyStruct()
        OneMemberStruct(42)
        TwoMemberStruct((True, 0), 1.0)
        DocstringStruct(-1)

    validate(main.compile_function())


def test_backward_ref(validate):
    @guppy.struct
    class StructA:
        x: int

    @guppy.struct
    class StructB:
        y: StructA

    @guppy
    def main(a: StructA, b: StructB) -> None:
        StructB(a)

    validate(main.compile_function())


def test_forward_ref(validate):
    @guppy.struct
    class StructA:
        x: "StructB"

    @guppy.struct
    class StructB:
        y: int

    @guppy
    def main(a: StructA, b: StructB) -> None:
        StructA(b)

    validate(main.compile_function())


def test_generic(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.struct
    class StructA(Generic[T]):
        x: tuple[int, T]

    @guppy.struct
    class StructC:
        a: StructA[int]
        b: StructA[list[bool]]
        c: "StructB[float, StructB[bool, int]]"

    @guppy.struct
    class StructB(Generic[S, T]):
        x: S
        y: StructA[T]

    @guppy
    def main(a: StructA[StructA[float]], b: StructB[bool, int], c: StructC) -> None:
        x = StructA((0, False))
        y = StructA((0, -5))
        StructA((0, x))
        StructB(x, a)
        StructC(y, StructA((0, [])), StructB(42.0, StructA((4, b))))

    validate(main.compile_function())


def test_methods(validate):
    @guppy.struct
    class StructA:
        x: int

        @guppy
        def foo(self: "StructA", y: int) -> int:
            return 2 * self.x + y

    @guppy.struct
    class StructB:
        x: int
        y: float

        @guppy
        def bar(self: "StructB", a: StructA) -> float:
            return a.foo(self.x) + self.y

    @guppy
    def main(a: StructA, b: StructB) -> tuple[int, float]:
        return a.foo(1), b.bar(a)

    validate(main.compile_function())


def test_higher_order(validate):
    T = guppy.type_var("T")

    @guppy.struct
    class Struct(Generic[T]):
        x: T

    @guppy
    def factory(mk_struct: "Callable[[int], Struct[int]]", x: int) -> Struct[int]:
        return mk_struct(x)

    @guppy
    def main() -> None:
        factory(Struct, 42)

    validate(main.compile_function())


def test_wiring(validate):
    @guppy.struct
    class MyStruct:
        x: int

    @guppy
    def foo() -> MyStruct:
        s = 0
        # This tests that reassigning `s` invalidates the old `s = 0` wire when
        # compiling to Hugr.
        s = MyStruct(42)
        return s

    validate(foo.compile_function())


def test_field_access_and_drop(validate):
    @guppy.struct
    class MyStruct:
        x: int
        y: float
        z: tuple[int, int]

    @guppy
    def foo() -> float:
        # Access a field of an unnamed struct,
        # dropping all the other fields
        return MyStruct(42, 3.14, (1, 2)).y

    validate(foo.compile_function())


def test_redefine(validate):
    """See https://github.com/quantinuum/guppylang/issues/1107"""

    @guppy.struct
    class MyStruct:
        x: int

    @guppy.struct
    class MyStruct:  # noqa: F811
        pass

    @guppy
    def foo() -> MyStruct:
        return MyStruct()

    validate(foo.compile_function())
