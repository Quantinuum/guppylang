from guppylang import guppy
from guppylang.std.builtins import comptime, nat, Function


@guppy
def main(f: Function[[nat @ comptime], None]) -> None:
    pass


main.compile_function()
