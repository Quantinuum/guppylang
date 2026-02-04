from guppylang.decorator import custom_guppy_decorator, guppy


@custom_guppy_decorator
def my_guppy(f):
    return guppy(f)


def test_custom_decorator(validate):
    def make():
        @my_guppy
        def foooo() -> int:
            return 1 + bar()

        return foooo

    foo = make()

    @guppy
    def bar() -> int:
        return 2 + foo()

    @my_guppy
    def main() -> int:
        return foo() + bar() + main()

    validate(main.compile_function())


def test_nested(validate):
    def my_guppy():
        @custom_guppy_decorator
        def inner(f):
            return guppy(f)

        return inner

    def make():
        @my_guppy()
        def foooo() -> int:
            return 1 + bar()

        return foooo

    foo = make()

    @guppy
    def bar() -> int:
        return 2 + foo()

    @my_guppy()
    def main() -> int:
        return foo() + bar() + main()

    validate(main.compile_function())


def test_method(validate):
    class MyGuppy:
        @custom_guppy_decorator
        def decorator(self, f):
            return guppy(f)

    my_guppy = MyGuppy()

    def make():
        @my_guppy.decorator
        def foooo() -> int:
            return 1 + bar()

        return foooo

    foo = make()

    @guppy
    def bar() -> int:
        return 2 + foo()

    @my_guppy.decorator
    def main() -> int:
        return foo() + bar() + main()

    validate(main.compile_function())
