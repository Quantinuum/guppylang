from guppylang.decorator import guppy

T = guppy.type_var("T", copyable=True, droppable=True)


@guppy.struct
class MyStruct[x: T]:
    pass


MyStruct.compile()
