from guppylang.decorator import guppy
from guppylang.std.angles import pi
from guppylang.std.global_phase import global_phase


@guppy
def test() -> None:
    global_phase(pi)


test.compile_function()
