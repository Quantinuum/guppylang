from guppylang.decorator import guppy


@guppy.struct
class MyStruct(metaclass=type):
    x: int


MyStruct.compile()
