from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    var1 = {"x": int, "x": bool}


MyEnum.compile()
