"""File used to test the filename table in debug info metadata."""

from guppylang import guppy
from guppylang.std.quantum import qubit
from pytket import Circuit


@guppy
def bar() -> None:  # MARKER:def_bar
    # Leave white space to check scope_line is set correctly.

    pass  # MARKER:scope_bar


@guppy.declare
def baz() -> None: ...  # MARKER:def_baz


@guppy.comptime
def comptime_bar() -> None:  # MARKER:def_comptime_bar
    pass  # MARKER:scope_comptime_bar


circ = Circuit(1)
circ.H(0)

pytket_bar_load = guppy.load_pytket(  # MARKER:def_pytket_bar_load
    "pytket_bar_load", circ, use_arrays=False
)


@guppy.pytket(circ)
def pytket_bar_stub(q1: qubit) -> None: ...  # MARKER:def_pytket_bar_stub
