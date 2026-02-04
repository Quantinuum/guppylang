from typing import Generic
from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.struct
class MyStruct(Generic[T]):
    @guppy
    def foo(self: "MyStruct[T]") -> None:
        pass


@guppy
def main(s: MyStruct[int]) -> None:
    s.foo[float]()


main.compile()
