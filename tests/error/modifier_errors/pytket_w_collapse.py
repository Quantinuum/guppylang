from pytket.circuit import Circuit, OpType
from guppylang import guppy, qubit

circ = Circuit(1)
circ.H(0)
circ.add_gate(OpType.Collapse, [0])

@guppy.pytket(circ)
def guppy_circ(q: qubit) -> None: ...

@guppy(unitary=True)
def foo(q: qubit) -> None:
    guppy_circ(q)


foo.check()