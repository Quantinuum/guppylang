from typing import Generic

from guppylang.decorator import guppy

X = guppy.const_var("X", "float[int]")


@guppy.struct
class Struct(Generic[X]):
    pass


@guppy
def main(_: Struct[X]) -> None:
    pass


main.compile_function()
