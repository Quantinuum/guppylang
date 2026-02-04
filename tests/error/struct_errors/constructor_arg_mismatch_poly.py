from typing import Generic

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.struct
class MyStruct(Generic[T]):
    x: T
    y: T


@guppy
def main() -> None:
    MyStruct(0, False)


main.compile()
