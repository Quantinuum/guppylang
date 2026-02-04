from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int = 42


MyStruct.compile()
