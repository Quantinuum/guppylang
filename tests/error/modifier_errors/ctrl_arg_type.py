from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import control


@guppy
def test() -> None:
    x = qubit()
    with control(x, True):
        pass


test.compile()
