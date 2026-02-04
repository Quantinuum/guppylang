from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> None:
    array(1, False)


main.compile()