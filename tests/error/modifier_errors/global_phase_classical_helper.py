from guppylang.decorator import guppy
from guppylang.std.angles import pi
from guppylang.std.builtins import control
from guppylang.std.global_phase import global_phase
from guppylang.std.quantum import qubit


@guppy
def helper() -> None:
    global_phase(pi)


@guppy
def test(c: qubit) -> None:
    with control(c):
        helper()


test.compile_function()
