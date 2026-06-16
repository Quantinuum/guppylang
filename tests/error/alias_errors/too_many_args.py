from typing import Generic

from guppylang import guppy


T = guppy.type_var("T")


@guppy.struct
class Box(Generic[T]):
    value: T


# Too many type args for generic alias (Box[T] takes 1, given 2)
BoxAlias = guppy.type_alias("BoxAlias", "Box[T]", params=[T])


@guppy
def main(b: BoxAlias[int, bool]) -> int:
    return b.value


main.compile_function()
