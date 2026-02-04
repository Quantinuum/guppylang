from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import discard


@guppy.struct
class S:
    x: int
    q: qubit


@guppy.declare
def bar(s: S) -> None: ...


@guppy.comptime
def foo(s: S @ owned) -> None:
    bar(s)
    # Remains immutable after an inout call
    s.x = 1
    discard(s.q)


foo.compile()
