from guppylang.decorator import guppy


@guppy.enum
class MyEnum(metaclass=type):
    var = {"x": int}


MyEnum.compile()
