from guppylang.decorator import guppy
from guppylang.std.angles import pi
from guppylang.std.global_phase import global_phase

T = guppy.type_var("T", copyable=False, droppable=False)


@guppy
def phase(x: T) -> T:
    global_phase(pi)
    return x


@guppy
def test(x: int) -> int:
    return phase(x)


test.compile_function()
