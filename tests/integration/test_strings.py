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


def test_enum(validate):
    @guppy.enum
    class StringEnum:
        Var1 = {"x": str}

    @guppy
    def main() -> StringEnum:
        return StringEnum.Var1("Lorem Ipsum")

    validate(main.compile_function())
