from guppylang import guppy, qubit
from guppylang.std.builtins import comptime


T = guppy.type_var("T", droppable=False)


@guppy
def main(q: T @comptime) -> None:
    pass


main.compile_function()
