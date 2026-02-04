from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    @guppy
    def x(self: "MyStruct") -> int:
        return 0

    x: int


@guppy
def main(s: MyStruct) -> None:
    s.x


main.compile()
