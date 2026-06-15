from guppylang import guppy
from guppylang.std.builtins import comptime, nat, Fn


@guppy
def main(f: Fn[[nat @comptime], None]) -> None:
    pass


main.compile_function()
