from guppylang.decorator import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import qubit


@guppy.struct
class Mixed:
    q: qubit
    n: int


@guppy
def test(s: Mixed) -> None:
    with dagger:
        s.n += 1


test.compile_function()
