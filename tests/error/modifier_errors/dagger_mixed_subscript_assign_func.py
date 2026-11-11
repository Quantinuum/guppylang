from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy.struct
class Mixed:
    q: qubit
    n: int


@guppy(daggerable=True)
def index(s: Mixed) -> int:
    return s.n


@guppy(daggerable=True)
def test(xs: array[int, 2], s: Mixed) -> None:
    xs[index(s)] = 1


test.compile_function()
