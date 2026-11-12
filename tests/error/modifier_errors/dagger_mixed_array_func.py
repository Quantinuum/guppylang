from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import h, qubit


@guppy.struct
class Mixed:
    q: qubit
    n: int


@guppy(daggerable=True)
def foo(xs: array[Mixed, 2]) -> None:
    h(xs[0].q)


@guppy(daggerable=True)
def test(xs: array[Mixed, 2]) -> None:
    foo(xs)


test.compile_function()
