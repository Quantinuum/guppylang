from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=True)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(frozen=False)
class MyStruct2:
    y: int


@guppy
def foo(s: MyStruct1 @owned, b: bool) -> int:
    t = s.x
    if b:
        return s.x.y
    return 0


foo.compile()
