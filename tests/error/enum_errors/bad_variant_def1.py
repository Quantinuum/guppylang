from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    v1 = 20


MyEnum.compile()
