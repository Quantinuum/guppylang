from guppylang.decorator import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import qubit, x


@guppy
def test(t: tuple[qubit, qubit]) -> None:
    with control(t[0]):
        x(t[0])


test.compile_function()
