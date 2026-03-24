from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class MyEnum:
    Left = {} 

@guppy
def g(e : MyEnum) -> None:
    pass

@compile_guppy
def fun() -> None:
    g(MyEnum)
