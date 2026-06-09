from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy.declare
def bar(s: MyStruct @ owned) -> bool: ...


@guppy
def foo(ss: list[MyStruct] @ owned) -> None:
    [s.x for s in ss if bar(s)]


foo.compile()
