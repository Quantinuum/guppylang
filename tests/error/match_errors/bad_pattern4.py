from tests.util import compile_guppy
from guppylang import guppy

@guppy.struct
class MyStruct:
    x: int

@compile_guppy
def foo(s: MyStruct) -> None:
    MyStruct = 42
    match s:
        case MyStruct():
            pass


