from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy.declare
def bar(s: MyStruct @ owned) -> bool: ...


@guppy
def foo(s: MyStruct @ owned) -> None:
    t = s
    [s.x for _ in range(10)]


foo.compile()
