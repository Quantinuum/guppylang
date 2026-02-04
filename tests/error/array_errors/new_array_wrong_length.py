from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> array[int, 2]:
    return array(1, 2, 3)


main.compile()