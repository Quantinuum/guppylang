from typing import Generic

from hugr import tys
from guppylang import guppy
from guppylang_internals.decorator import custom_type


@custom_type(tys.Tuple(), droppable=False)
class MyType:
    pass


X = guppy.const_var("X", "MyType")


@guppy.struct
class Struct(Generic[X]):
    pass


@guppy
def main(_: Struct[X]) -> None:
    pass


main.compile_function()
