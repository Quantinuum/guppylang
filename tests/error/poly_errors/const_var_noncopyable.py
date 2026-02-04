from typing import Generic

from guppylang.decorator import guppy
from guppylang.std.quantum import qubit

Q = guppy.const_var("Q", "qubit")


@guppy.struct
class Struct(Generic[Q]):
    pass


@guppy
def main(_: Struct[Q]) -> None:
    pass


main.compile_function()
