from guppylang import guppy
from guppylang.std.builtins import comptime
from guppylang.std.array import array


@guppy.struct
class MyStruct:
    @guppy
    def method(self, x: int @ comptime) -> array[int, 3]:
        return array(x for _ in range(3))

lib = guppy.library(MyStruct).compile()
