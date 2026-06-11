from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    x: int

    @guppy
    def __bool__(self) -> bool:
        return self.x > 0


@guppy
def foo(s: MyStruct @owned, b: bool) -> MyStruct:
    if b or (t := s):
        return s
    return MyStruct(0)


foo.compile()
