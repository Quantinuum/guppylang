from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> array[int, 1]:
    array(False)


main.compile()