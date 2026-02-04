from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

@guppy.declare
def use(x: qubit @ owned) -> None: ...

@compile_guppy
def foo(b: bool) -> tuple[qubit, int]:
    t = (qubit(), 100)
    if b:
        use(t[0])
    return t