from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

@guppy.declare
def use(x: qubit @ owned) -> None: ...

@guppy.declare
def use_tup(t: tuple[qubit, int] @ owned) -> None: ...

@compile_guppy
def foo() -> None:
    t = (qubit(), 100)
    use(t[0])
    use_tup(t)
