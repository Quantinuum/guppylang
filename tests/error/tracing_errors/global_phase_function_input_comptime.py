from guppylang.decorator import guppy
from guppylang.std.angles import pi
from guppylang.std.global_phase import global_phase
from guppylang.std.lang import Function
from guppylang.std.quantum import qubit


@guppy.comptime
def test(f: Function[[qubit], None]) -> None:
    global_phase(pi)


test.compile_function()
