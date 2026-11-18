from guppylang.decorator import guppy
from guppylang.std.builtins import array, dagger
from guppylang.std.quantum import h, qubit


@guppy.struct
class Mixed:
    q: qubit
    n: int


@guppy
def test(xs: array[Mixed, 2], i: int) -> None:
    with dagger:
        h(xs[i].q)


test.compile_function()
