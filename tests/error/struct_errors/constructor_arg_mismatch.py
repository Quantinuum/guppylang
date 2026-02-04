from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: tuple[int, int]


@guppy
def main() -> None:
    MyStruct(0)


main.compile()
