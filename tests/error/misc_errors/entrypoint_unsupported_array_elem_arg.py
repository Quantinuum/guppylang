from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.num import nat


@guppy
def foo(x: array[nat, 3]) -> None:
    pass


foo.emulator(1)
