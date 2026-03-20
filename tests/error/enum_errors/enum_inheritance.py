from guppylang.decorator import guppy


@guppy.enum
class MyEnum(int):
    var = {"x": bool}


MyEnum.compile()
