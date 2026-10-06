from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    class OtherClass:
        VALUE = 1


MyEnum.compile()
