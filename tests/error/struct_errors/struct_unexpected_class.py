from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    class MyEnum:
        VALUE = 1


MyStruct.compile()
