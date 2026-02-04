from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit, discard
from guppylang.std.builtins import owned

@guppy
def use(x: qubit @ owned) -> qubit:
    return x

@compile_guppy
def foo() -> None:
    t = (11, qubit(), 22)
    q1 = use(t[1])
    q2 = use(t[1])
    discard(q1)
    discard(q2)

