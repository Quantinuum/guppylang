from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> array[int, 42]:
    return array(i for i in range(10))


main.compile()
