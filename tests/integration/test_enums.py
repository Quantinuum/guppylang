"""
The syntax is inspired by Rust:

enum Message {
    Quit,
    Resize { width: i32, height: i32},
    Move {x: u64, y: u64},
}

fn main() {
    let messages: [Message; 5] = [
        Message::Resize {
            width: 10,
            height: 30,
        },
        Message::Move { x: 10, y: 15 },
        Message::Quit,
    ];

}
"""

from guppylang import guppy
from tests.util import compile_guppy

from typing import Generic, TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


def test_basic_enum(validate):
    @guppy.enum
    class EmptyEnum:
        pass

    @guppy.enum
    class OneVariantEnum:
        VariantA = {}

    @guppy.enum
    class TwoVariantEnum:
        VariantA = {}
        VariantB = {"x": int, "y": float}

    @guppy.enum
    class DocstringEnum:
        """This is an enum with a docstring!"""

        VariantA = {}
        VariantB = {"x": int}

    @guppy.enum
    class MethodEnum:
        Empty = {}
        Resize = {"width": int, "height": int}
        Quit = {"x": int}

        @guppy
        def method(self) -> str:
            return "42"

    @compile_guppy
    def main(
        e: EmptyEnum,
        one: OneVariantEnum,
        two: TwoVariantEnum,
        doc: DocstringEnum,
        meth: MethodEnum,
    ) -> None:
        var1 = OneVariantEnum.VariantA()
        two_var1 = TwoVariantEnum.VariantA()
        two_var2 = TwoVariantEnum.VariantB(1, 2.0)
        var3 = DocstringEnum.VariantB(3)
        var4 = DocstringEnum.VariantA()
        variant1 = MethodEnum.Resize(2, 3)
        variant2 = MethodEnum.Quit(1)
        variant3 = MethodEnum.Empty()
        variant1.method()
        variant2.method()
        variant3.method()

    validate(main)


def test_backward_ref_enum(validate):
    @guppy.enum
    class EnumA:
        VariantA = {"x": int}

    @guppy.enum
    class EnumB:
        VariantB = {"y": EnumA}

    @guppy
    def main(a: EnumA, b: EnumB) -> EnumB:
        e1 = EnumB.VariantB(a)
        return EnumB.VariantB(EnumA.VariantA(1))

    validate(main.compile_function())


def test_forward_ref(validate):
    @guppy.enum
    class EnumA:
        VariantA = {"x": "EnumB"}  # Forward reference

    @guppy.enum
    class EnumB:
        VariantB = {"y": int}

    @guppy
    def main(a: EnumA, b: EnumB) -> EnumA:
        EnumA.VariantA(b)
        return EnumA.VariantA(EnumB.VariantB(1))

    validate(main.compile_function())


def test_wiring(validate):
    @guppy.enum
    class MyEnum:
        VariantA = {"x": int}

    @guppy
    def foo() -> MyEnum:
        s = 0
        # This tests that reassigning `s` invalidates the old `s = 0` wire when
        # compiling to Hugr.
        s = MyEnum.VariantA(42)
        return s

    validate(foo.compile_function())


def test_redefine(validate):
    @guppy.enum
    class MyEnum:
        VariantA = {"x": int}

    @guppy.enum
    class MyEnum:  # noqa: F811
        VariantB = {}

    @guppy
    def foo() -> MyEnum:
        return MyEnum.VariantB()

    validate(foo.compile_function())


# TODO: Methods now are limited due to the fact that we cannot access to enum fields in
# and we do not have pattern matching
def test_methods(validate):
    @guppy.enum
    class EnumA:
        VariantA = {"x": int}

        @guppy
        def foo(self: "EnumA", y: int) -> int:
            return 2 + y

    @guppy.enum
    class EnumB:
        VariantA = {"x": int, "y": float}

        @guppy
        def bar(self: "EnumB", a: EnumA) -> float:
            return a.foo(6) + 5.1

    @guppy
    def main(a: EnumA, b: EnumB) -> tuple[int, float]:
        return a.foo(1), b.bar(a)

    validate(main.compile_function())


def test_generic_explicit(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.enum
    class EnumA(Generic[T]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {"x": tuple[int, T]}

    @guppy.enum
    class EnumC:
        VariantA = {"a": EnumA[int]}
        VariantB = {"b": EnumA[list[bool]]}
        VariantC = {"c": "EnumB[float, EnumB[bool, int]]"}

    @guppy.enum
    class EnumB(Generic[S, T]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {"x": S, "y": EnumA[T]}

    @guppy
    def main(a: EnumA[EnumA[float]], b: EnumB[bool, int], c: EnumC) -> None:
        x = EnumA.VariantA[bool]((0, False))
        y = EnumA.VariantA[int]((0, -5))
        EnumA.VariantA[EnumA[bool]]((0, x))
        EnumB.VariantA[int, EnumA[float]](42, a)
        EnumC.VariantA(y)
        EnumC.VariantB(EnumA.VariantA[list[bool]]((0, [])))
        EnumC.VariantC(
            EnumB.VariantA[float, EnumB[bool, int]](
                42.0, EnumA.VariantA[EnumB[bool, int]]((0, b))
            )
        )

    validate(main.compile_function())


def test_generic_infer(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.enum
    class EnumA(Generic[T]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {"x": tuple[int, T]}

    @guppy.enum
    class EnumC:
        VariantA = {"a": EnumA[int]}
        VariantB = {"b": EnumA[list[bool]]}
        VariantC = {"c": "EnumB[float, EnumB[bool, int]]"}

    @guppy.enum
    class EnumB(Generic[S, T]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {"x": S, "y": EnumA[T]}

    @guppy
    def main(a: EnumA[EnumA[float]], b: EnumB[bool, int], c: EnumC) -> None:
        x = EnumA.VariantA((0, False))
        y = EnumA.VariantA((0, -5))
        EnumA.VariantA((0, x))
        EnumB.VariantA(42, a)
        EnumC.VariantA(y)
        EnumC.VariantB(EnumA.VariantA((0, [])))
        EnumC.VariantC(EnumB.VariantA(42.0, EnumA.VariantA((0, b))))

    validate(main.compile_function())


def test_higher_order(validate):
    T = guppy.type_var("T")

    @guppy.enum
    class Enum(Generic[T]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {"x": T}

    @guppy
    def factory(mk_enum: "Callable[[int], Enum[int]]", x: int) -> Enum[int]:
        return mk_enum(x)

    @guppy
    def main() -> None:
        factory(Enum.VariantA, 42)

    validate(main.compile_function())
