from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import h, qubit


@guppy.struct
class Mixed:
    q: qubit
    n: int


@guppy(daggerable=True)
def index(s: Mixed) -> int:
    return s.n


@guppy(daggerable=True)
def test(qs: array[qubit, 2], js: array[int, 2], s: Mixed) -> None:
    h(qs[js[index(s)]])


test.compile_function()
