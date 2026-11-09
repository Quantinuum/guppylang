from guppylang.decorator import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import qubit, x


@guppy.struct
class TwoQubits:
    a: qubit
    b: qubit


@guppy
def test(tq: TwoQubits) -> None:
    with control(tq.a):
        x(tq.a)


test.compile_function()
