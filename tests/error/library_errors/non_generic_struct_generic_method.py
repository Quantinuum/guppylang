from guppylang import guppy
from guppylang.std.array import array

T = guppy.type_var("T")

@guppy.struct
class MyStruct:
    @guppy
    def method(self, x: T) -> array[T, 3]:
        return array(x for _ in range(3))

lib = guppy.library(MyStruct).compile()
