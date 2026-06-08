from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy
def foo(s: MyStruct @owned, b: bool) -> int:
    while b:
        if b:
            t = s
            break
        a = s.x  # Ok
    return s.x


foo.compile()
