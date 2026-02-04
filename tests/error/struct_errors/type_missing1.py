from guppylang.decorator import guppy


x = 42


@guppy.struct
class MyStruct:
    x


MyStruct.compile()
