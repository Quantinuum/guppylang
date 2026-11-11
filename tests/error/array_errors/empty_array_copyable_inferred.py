from guppylang.decorator import guppy
from guppylang.std.array import array, empty_array


@guppy
def main() -> array[int, 2]:
    xs: array[int, 2] = empty_array()
    return xs

main.compile()
