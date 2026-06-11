from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.struct(frozen=False)
class MyStruct:
    pass


@guppy
def foo(s: MyStruct @owned) -> MyStruct:
    t = s  # Empty mutable structs are stiff affine
    return s


foo.compile()
