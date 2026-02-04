from typing import Generic

from guppylang.decorator import guppy

T = guppy.type_var("T")
n = guppy.nat_var("n")

# We don't yet support const vars referencing previously bound parameters
X = guppy.const_var("X", "array[T, n]")


@guppy.struct
class Struct(Generic[T, n, X]):
    pass


@guppy
def main(_: Struct[T, n, X]) -> None:
    pass


main.compile_function()
