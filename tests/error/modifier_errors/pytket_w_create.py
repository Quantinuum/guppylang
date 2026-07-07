from pytket.circuit import Circuit, OpType, Qubit
from guppylang import guppy, qubit

circ = Circuit(1)
circ.H(0)
circ.qubit_create(Qubit(0))

@guppy.pytket(circ)
def guppy_circ(q: qubit) -> None: ...

@guppy(unitary=True)
def foo(q: qubit) -> bool:
    guppy_circ(q)
    return True


foo.check()