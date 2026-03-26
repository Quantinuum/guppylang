"""File used to test the filename table in debug info metadata."""

from guppylang import guppy
from guppylang.std.quantum import qubit
from pytket import Circuit


@guppy
def bar() -> None:
    # Leave white space to check scope_line is set correctly.

    pass


@guppy.declare
def baz() -> None: ...


@guppy.comptime
def comptime_bar() -> None:
    pass


circ = Circuit(1)
circ.H(0)

pytket_bar_load = guppy.load_pytket("pytket_bar_load", circ, use_arrays=False)


@guppy.pytket(circ)
def pytket_bar_stub(q1: qubit) -> None: ...
