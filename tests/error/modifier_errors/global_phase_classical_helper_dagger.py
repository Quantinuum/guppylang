from guppylang.decorator import guppy
from guppylang.std.angles import pi
from guppylang.std.builtins import control
from guppylang.std.global_phase import global_phase
from guppylang.std.lang import dagger
from guppylang.std.quantum import qubit


@guppy
def helper() -> None:
    with dagger:
        global_phase(pi / 3)


@guppy
def test(c: qubit) -> None:
    with control(c):
        helper()


test.compile_function()
