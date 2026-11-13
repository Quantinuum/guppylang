from guppylang.decorator import guppy
from guppylang.std.array import empty_array


@guppy
def main() -> None:
    xs = empty_array[bool, 2]()
    xs.put(True, 0)
    xs.put(False, 1)

main.compile()
