from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main(n: int) -> None:
    array(i for i in range(n))


main.compile_function()
