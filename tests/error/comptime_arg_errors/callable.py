from collections.abc import Callable

from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def main(f: Callable[[nat @comptime], None]) -> None:
    pass


main.compile_function()
