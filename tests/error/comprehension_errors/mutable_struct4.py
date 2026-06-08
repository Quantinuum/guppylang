from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy.declare
def bar(s: MyStruct @ owned) -> bool: ...


@guppy
def foo(s: MyStruct @ owned) -> None:
    [0 for _ in range(10) if bar(s)]


foo.compile()
