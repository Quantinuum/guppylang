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

    @guppy
    def main(t: Test) -> int:
        return t.foo()

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


@pytest.mark.skip("See https://github.com/quantinuum/guppylang/issues/456")
def test_struct_redefinition(validate):
    @guppy.struct
    class Test:
        x: "blah"  # Non-existing type  # noqa: F821

    @guppy.struct
    class Test:  # noqa: F811
        y: int

    @guppy
    def main(x: int) -> Test:
        return Test(x)

    validate(main.compile_function())


@pytest.mark.skip("See https://github.com/quantinuum/guppylang/issues/456")
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

    @guppy
    def main(x: int) -> int:
        return Test(x).bar()

    validate(main.compile_function())
