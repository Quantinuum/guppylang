from guppylang.std.builtins import array, control
from pytket.circuit import Circuit
from guppylang import guppy, qubit

circ = Circuit(1)
circ.H(0)
circ.Reset(0)

guppy_circ = guppy.load_pytket("circ", circ)

@guppy
def foo(c: qubit, q: array[qubit, 1]) -> None:
    with control(c):
        guppy_circ(q)
    


foo.check()