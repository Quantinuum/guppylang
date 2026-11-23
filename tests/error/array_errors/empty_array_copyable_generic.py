from guppylang.decorator import guppy
from guppylang.std.array import array, empty_array
from guppylang.std.lang import owned

T = guppy.type_var("T", copyable=False, droppable=False)


@guppy
def singleton(x: T @ owned) -> array[T, 1]:
    xs = empty_array[T, 1]()
    xs.put(x, 0)
    return xs


@guppy
def main() -> array[bool, 1]:
    return singleton(True)

main.compile()
