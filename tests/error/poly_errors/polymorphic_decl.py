from typing import Generic

from guppylang.decorator import guppy

F = guppy.const_var("F", "float")


@guppy.struct
class Struct(Generic[F]):
    pass


@guppy.declare
def main(_: Struct[F]) -> float: ...


main.compile()
