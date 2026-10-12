from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import angle, h, measure, qubit, rx


@guppy
def classical_helper(n: int, c: qubit) -> int:
    q = qubit()
    h(q)
    if measure(q):
        return n * 2
    else:
        return n


@guppy
def test(q: qubit, c: qubit) -> None:
    with control(c):
        rx(q, angle(1 / classical_helper(2, c)))


test.compile_function()
