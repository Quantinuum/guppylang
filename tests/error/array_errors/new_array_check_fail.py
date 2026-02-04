from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> int:
    return array(1)


main.compile()