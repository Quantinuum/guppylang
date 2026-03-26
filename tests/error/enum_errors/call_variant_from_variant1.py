from turtle import st

from guppylang import guppy
from guppylang.std.either import R
from tests.util import compile_guppy


@guppy.enum
class MyEnum:
    Left = {}
    Right = {}

@guppy
def fun() -> None:
    l = MyEnum.Left()
    l.Right()


fun.check()
