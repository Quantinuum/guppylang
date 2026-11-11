from guppylang.decorator import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import qubit


@guppy.struct
class TwoQubits:
    a: qubit
    b: qubit


@guppy.declare(controllable=True)
def use(tq: TwoQubits) -> None: ...


@guppy
def test(tq: TwoQubits) -> None:
    with control(tq.a):
        use(tq)


test.compile_function()
