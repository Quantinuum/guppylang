from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> None:
    array(i for i in range(100) if i % 2 == 0)


main.compile()
