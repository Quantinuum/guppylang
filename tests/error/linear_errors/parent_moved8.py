from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy
def foo(s: MyStruct @owned) -> None:
    t = s
    s.x = 1


foo.compile()
