from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def foo(x: array[array[float, 3], 2]) -> None:
    pass


foo.emulator(1)
