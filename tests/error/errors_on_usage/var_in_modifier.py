from guppylang.decorator import guppy
from guppylang.std.builtins import control, qubit

@guppy
def test(b: bool, q: qubit) -> int:
    with control(q):
        x = 3
    return x +1


test.check()
