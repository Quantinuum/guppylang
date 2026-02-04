from guppylang.decorator import guppy
from tests.util import compile_guppy


def test_basic_type(validate):
    @compile_guppy
    def foo(x: str) -> str:
        return x

    validate(foo)


def test_basic_value(validate):
    @compile_guppy
    def foo() -> str:
        x = "Hello World"
        return x

    validate(foo)


def test_struct(validate):
    @guppy.struct
    class StringStruct:
        x: str

    @guppy
    def main(s: StringStruct) -> None:
        StringStruct("Lorem Ipsum")

    validate(main.compile_function())
