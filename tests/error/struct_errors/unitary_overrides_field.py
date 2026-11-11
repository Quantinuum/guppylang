from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int

    @guppy.unitary
    class x:
        @guppy
        def __call__(self: "MyStruct") -> None:
            pass


@guppy
def main(s: MyStruct) -> None:
    s.x


main.compile()
