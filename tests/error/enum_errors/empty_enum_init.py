from guppylang import guppy

@guppy.enum
class MyEnum:
    pass

@guppy
def fun() -> None:
    x = MyEnum()

fun.compile()