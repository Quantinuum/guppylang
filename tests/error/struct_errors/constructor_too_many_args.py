from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int


@guppy
def main() -> None:
    MyStruct(1, 2, 3)


main.compile()
