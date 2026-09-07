from pytket.circuit import Circuit
from guppylang import guppy, qubit

circ = Circuit(1)
circ.H(0)
circ.measure_all()

@guppy.pytket(circ)
def guppy_circ(q: qubit) -> bool: ...

@guppy(unitary=True)
def foo(q: qubit) -> bool:
    b = guppy_circ(q)
    return b


foo.check()