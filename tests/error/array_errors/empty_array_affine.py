from guppylang import guppy
from guppylang.std.array import empty_array


@guppy.struct
class Item:
    value: int


@guppy
def main() -> None:
    values = empty_array[Item, 1]()


main.compile_function()
