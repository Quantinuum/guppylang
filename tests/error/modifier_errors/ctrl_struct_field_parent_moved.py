from guppylang.decorator import guppy
from guppylang.std.builtins import control, owned
from guppylang.std.quantum import discard, qubit


@guppy.struct
class TwoQubits:
    q: qubit
    i: int


@guppy.declare
def use(i: int) -> None: ...


@guppy.declare
def owe(tq: TwoQubits @ owned) -> None: ...


@guppy
def test() -> None:
    tq = TwoQubits(qubit(), 0)
    c = qubit()
    a = tq
    with control(c):
        use(tq.i)
    owe(a)
    discard(c)


test.compile_function()
