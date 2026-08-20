from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: bool

@guppy.struct
class OtherStruct(MyStruct):
    pass

OtherStruct.compile()
