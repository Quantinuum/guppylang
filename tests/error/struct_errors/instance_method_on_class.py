from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    field: int

    @guppy
    def foo(self: "MyStruct") -> None:
        pass


@guppy
def main() -> None:
    MyStruct.foo()


main.compile()
