from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy
def foo(s: MyStruct @owned, b: bool) -> int:
    if b:
        t = s
    return s.x


foo.compile()
