import pytest

from guppylang.decorator import guppy
from guppylang_internals.error import GuppyError


def test_func_redefinition(validate):
    @guppy
    def test() -> bool:
        return 5  # Type error on purpose

    @guppy
    def test() -> bool:  # noqa: F811
        return False

    validate(test.compile_function())


def test_method_redefinition(validate):
    @guppy.struct
    class Test:
        x: int

        @guppy
        def foo(self: "Test") -> int:
            return 1.0  # Type error on purpose

        @guppy
        def foo(self: "Test") -> int:  # noqa: F811
            return 1  # Type error on purpose

    @guppy.enum
    class MyEnum:
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self) -> float:
            return 2.0

        @guppy
        def foo(self) -> int:  # noqa: F811
            return 2

    @guppy
    def main(t: Test, e: MyEnum) -> int:
        return t.foo() + e.foo()

    validate(main.compile_function())


def test_redefine_after_error(validate):
    @guppy.struct
    class Foo:
        x: int

    @guppy
    def foo() -> int:
        return y  # noqa: F821

    with pytest.raises(GuppyError):
        foo.compile_function()

    @guppy.struct
    class Foo:  # noqa: F811
        x: int

    @guppy
    def foo(f: Foo) -> int:
        return f.x

    validate(foo.compile_function())

    @guppy.enum
    class Bar:
        VariantA = {}  # noqa: RUF012

    @guppy
    def bar() -> int:
        return y  # noqa: F821

    with pytest.raises(GuppyError):
        bar.compile_function()

    @guppy.enum
    class Bar:  # noqa: F811
        VariantA = {"x": int}  # noqa: RUF012

        @guppy
        def foo(self) -> int:
            return 22

    @guppy
    def bar(b: Bar) -> int:
        return b.foo()

    validate(bar.compile_function())


def test_struct_redefinition(validate):
    @guppy.struct
    class Test:
        x: "blah"  # Non-existing type  # noqa: F821

    @guppy.struct
    class Test:  # noqa: F811
        y: int

    @guppy.enum
    class MyEnum:
        VariantB = {"x": "blah"}  # noqa: RUF012

    @guppy.enum
    class MyEnum:  # noqa: F811
        VariantB = {"x": int}  # noqa: RUF012

    @guppy
    def main(x: int) -> Test:
        e = MyEnum.VariantB(x)
        return Test(x)

    validate(main.compile_function())


def test_struct_method_redefinition(validate):
    @guppy.struct
    class Test:
        x: int

        @guppy
        def foo(self: "Test") -> int:
            return 1.0  # Type error on purpose

    @guppy.struct
    class Test:  # noqa: F811
        y: int

        @guppy
        def bar(self: "Test") -> int:
            return self.y

    @guppy.enum
    class MyEnum:
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self) -> float:
            return 2.0

    @guppy.enum
    class MyEnum:  # noqa: F811
        VariantA = {}  # noqa: RUF012

        @guppy
        def foo(self) -> int:
            return 2

    @guppy
    def main(x: int) -> int:
        e = MyEnum.VariantA()
        return Test(x).bar() + e.foo()

    validate(main.compile_function())
