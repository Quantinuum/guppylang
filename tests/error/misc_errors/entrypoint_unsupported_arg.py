from guppylang.decorator import guppy
from guppylang.std.num import nat


@guppy
def foo(x: nat) -> None:
    pass


foo.emulator(1)
