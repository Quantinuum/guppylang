from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    var1 = {"x": int}  # noqa: RUF012
    var1 = {"x": bool}  # noqa: RUF012, PIE794


MyEnum.compile()
