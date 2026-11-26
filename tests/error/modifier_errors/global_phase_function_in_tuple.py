from guppylang.decorator import guppy
from guppylang.std.angles import pi
from guppylang.std.global_phase import global_phase
from guppylang.std.lang import Function
from guppylang.std.quantum import qubit


@guppy
def test(t: tuple[Function[[qubit], None], int]) -> None:
    global_phase(pi)


test.compile_function()
