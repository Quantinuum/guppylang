from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int
    y: bool


@guppy
def foo(s: MyStruct) -> None:
    s.x, a = (1, 2), 3


foo.compile()
