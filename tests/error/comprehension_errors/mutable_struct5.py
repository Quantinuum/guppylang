from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy.declare
def bar(s: MyStruct @ owned) -> list[int]: ...


@guppy
def foo(s: MyStruct @ owned) -> None:
    [0 for _ in range(20) for _ in bar(s)]


foo.compile()
