from turtle import st

from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class MyEnum:
    Left = {} 

    @guppy
    def method(self) -> str:
            return "42"

@guppy
def fun() -> None:
    a = MyEnum.method

fun.check()
