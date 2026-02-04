from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int
    """Docstring in wrong position"""
    y: bool


MyStruct.compile()
