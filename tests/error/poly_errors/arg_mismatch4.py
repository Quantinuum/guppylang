from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main(x: array[int, bool]) -> None:
    pass


main.compile_function()
