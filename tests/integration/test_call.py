from guppylang.decorator import guppy


def test_call(validate):
    @guppy
    def foo() -> int:
        return 42

    @guppy
    def bar() -> int:
        return foo()

    validate(bar.compile_function())


def test_call_back(validate):
    @guppy
    def foo(x: int) -> int:
        return bar(x)

    @guppy
    def bar(x: int) -> int:
        return x

    validate(foo.compile_function())


def test_recursion(validate):
    @guppy
    def main(x: int) -> int:
        return main(x)

    validate(main.compile_function())


def test_mutual_recursion(validate):
    @guppy
    def foo(x: int) -> int:
        return bar(x)

    @guppy
    def bar(x: int) -> int:
        return foo(x)

    validate(foo.compile_function())


def test_unary_tuple(validate):
    @guppy
    def foo(x: int) -> tuple[int]:
        return (x,)

    @guppy
    def bar(x: int) -> int:
        (y,) = foo(x)
        return y

    validate(bar.compile_function())


def test_method_call(validate):
    @guppy
    def foo(x: int) -> int:
        return x.__add__(2)

    validate(foo.compile_function())
