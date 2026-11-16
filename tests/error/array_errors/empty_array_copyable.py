from guppylang import guppy
from guppylang.std.array import empty_array
from guppylang.std.builtins import output


@guppy
def main() -> None:
    values = empty_array[bool, 1]()
    values.put(True, 0)
    output("value", values[0])


main.compile_function()
