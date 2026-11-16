from guppylang import guppy
from guppylang.std.array import empty_array


@guppy
def main() -> None:
    make_empty = empty_array[float, 0]
    values = make_empty()


main.compile_function()
