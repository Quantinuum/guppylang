from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> None:
    a = array(1, 2, 3)
    a[0] = "not an int"

main.compile()