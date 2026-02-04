from pytket import Circuit

from guppylang.decorator import guppy
from guppylang.std.quantum import qubit

circ = Circuit(2)
circ.X(0)
circ.Y(1)

@guppy.pytket(circ)
def guppy_circ(q: qubit) -> None: ...

@guppy
def foo(q: qubit) -> None:
    guppy_circ(q)


foo.compile()