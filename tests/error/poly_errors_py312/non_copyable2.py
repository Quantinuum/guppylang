from guppylang import qubit
from guppylang.decorator import guppy


@guppy.struct
class MyStruct[Q: qubit]:
    pass


MyStruct.compile()
