from guppylang import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import angle, h, measure, qubit, rx


@guppy
def classical_helper(n: int) -> int:
    q = qubit()
    h(q)
    if measure(q):
        return n * 2
    else:
        return n


@guppy
def test(q: qubit) -> None:
    with dagger:
        rx(q, angle(1 / classical_helper(2)))


test.compile_function()
