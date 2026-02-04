from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int

    @guppy
    def x(self: "MyStruct") -> int:
        return 0


@guppy
def main(s: MyStruct) -> None:
    s.x


main.compile()
