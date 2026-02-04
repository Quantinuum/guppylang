from guppylang import guppy, qubit
from guppylang.std.builtins import comptime


@guppy
def main(q: qubit @comptime) -> None:
    pass


main.compile_function()
