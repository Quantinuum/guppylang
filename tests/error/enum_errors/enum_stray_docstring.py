from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    v1 = {"x": int}
    """Docstring in wrong position"""
    v2 = {"y": bool}


MyEnum.compile()
