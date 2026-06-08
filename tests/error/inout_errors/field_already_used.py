from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=True)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(frozen=False)
class MyStruct2:
    y: int


@guppy.declare
def foo(s: MyStruct2) -> None: ...


@guppy.declare
def use(s: MyStruct2 @owned) -> None: ...


@guppy
def test(s: MyStruct1 @owned) -> None:
    use(s.x)
    foo(s.x)


test.compile()
