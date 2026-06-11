from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy
def foo(s: MyStruct @owned, b: bool) -> MyStruct:
    if b:
        t = s
    return s


foo.compile()
