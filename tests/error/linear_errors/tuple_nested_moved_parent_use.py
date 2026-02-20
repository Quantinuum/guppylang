from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

@guppy.declare
def use(x: qubit @ owned) -> None: ...

@compile_guppy
def foo() -> tuple[tuple[qubit, int], int]:
    t = ((qubit(), 1), 2)
    use(t[0][0])
    return t
