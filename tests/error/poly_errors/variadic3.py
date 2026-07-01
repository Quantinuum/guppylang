from guppylang.decorator import guppy


@guppy.struct
class MyStruct[*Ts]:
    pass


MyStruct.compile()
