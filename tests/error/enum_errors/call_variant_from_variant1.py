from guppylang import guppy


@guppy.enum
class MyEnum:
    Left = {}
    Right = {}

@guppy
def fun() -> None:
    l = MyEnum.Left()
    l.Right()


fun.check()
