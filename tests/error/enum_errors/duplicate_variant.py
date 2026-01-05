from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    var1 = {"x": int}
    var1 = {"x": bool}


MyEnum.compile()
