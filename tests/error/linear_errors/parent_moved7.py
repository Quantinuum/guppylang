from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=True)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(frozen=False)
class MyStruct2:
    y: int


@guppy
def foo(s: MyStruct1 @owned, b: bool) -> None:
    while b:
        a = s.x


foo.compile()
