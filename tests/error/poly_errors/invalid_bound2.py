from guppylang.decorator import guppy


@guppy.struct
class MyStruct[x: (42, 43)]:
    pass


MyStruct.compile()
