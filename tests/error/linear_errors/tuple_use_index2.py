from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

@guppy.declare
def use(x: qubit @ owned) -> None: ...

@guppy.struct
class S:
    t: tuple[qubit, int]

@compile_guppy
def foo(b: bool) -> S:
    s = S((qubit(), 1))
    use(s.t[0])
    return s