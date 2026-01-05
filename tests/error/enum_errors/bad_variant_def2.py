from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    v1: int


MyEnum.compile()
