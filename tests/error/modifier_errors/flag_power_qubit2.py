from guppylang import qubit, guppy
from guppylang.std.builtins import owned

@guppy.struct
class QubitPair:
    q1: qubit
    q2: qubit

@guppy.declare
def init_pair() -> QubitPair: ...

@guppy.declare(unitary=True)
def uni_discard(q: QubitPair @owned) -> None: ...


@guppy(power=True)
def test() -> None:
    qp = init_pair()
    uni_discard(qp)
    


test.compile()
