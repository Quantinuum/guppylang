from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class MyEnum:
    Left = {} 


@compile_guppy
def fun() -> None:
    x = MyEnum
