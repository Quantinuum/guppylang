from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> array[int, 50]:
    return array(0 for _ in range(10) for _ in range(5))


main.compile()
