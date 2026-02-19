from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

@guppy.declare
def use(x: qubit @ owned) -> None: ...

@guppy.struct
class S:
    t: tuple[qubit, int]

    @guppy
    def check(self) -> bool:
        return True

@compile_guppy
def foo() -> None:
    s = S((qubit(), 100))
    use(s.t[0])
    if s.check():
        pass
