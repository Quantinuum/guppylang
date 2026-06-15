from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(frozen=False)
class MyStruct2:
    y: int


@guppy
def foo(s: MyStruct1 @owned, b: bool) -> int:
    if b:
        s.x = MyStruct2(42)
    else:
        t = s
    return s.x.y


foo.compile()
