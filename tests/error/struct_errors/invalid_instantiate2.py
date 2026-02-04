from typing import Generic

from guppylang.decorator import guppy


T = guppy.type_var("T")


@guppy.struct
class MyStruct(Generic[T]):
    x: list[T]


@guppy
def foo(s: MyStruct[int, bool]) -> None:
    pass


foo.compile()
