from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int


@guppy
def foo(s: MyStruct @ owned) -> None:
    [s for _ in range(10)]



foo.compile()
