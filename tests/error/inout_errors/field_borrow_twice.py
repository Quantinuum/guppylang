from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=True)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(frozen=False)
class MyStruct2:
    y: int


@guppy.declare
def foo(s: MyStruct2, t: MyStruct2) -> None: ...


@guppy
def test(s: MyStruct1 @owned) -> None:
    foo(s.x, s.x)


test.compile()
