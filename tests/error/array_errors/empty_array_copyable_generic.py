from guppylang import guppy
from guppylang.std.array import array, empty_array
from guppylang.std.num import nat


@guppy
def make_empty[T, n: nat]() -> array[T, n]:
    return empty_array[T, n]()


@guppy
def main() -> None:
    values = make_empty[int, 0]()


main.compile_function()
