from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    v1 = {"x": int, "2": str}


MyEnum.compile()
