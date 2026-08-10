from typing import Generic

from guppylang import guppy


T = guppy.type_var("T")


@guppy.struct
class Box(Generic[T]):
    value: T


BoxAlias = guppy.type_alias("BoxAlias", "Box[T]", params=[T])


@guppy
def main(b: BoxAlias[int, bool]) -> int:  # Too many type args: BoxAlias takes 1
    return b.value


main.compile_function()
