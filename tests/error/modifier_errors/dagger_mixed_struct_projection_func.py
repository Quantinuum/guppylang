from guppylang.decorator import guppy
from guppylang.std.quantum import h, qubit


@guppy.struct
class Inner:
    q: qubit
    x: int


@guppy.struct
class Outer:
    inner: Inner
    q: qubit


@guppy(daggerable=True)
def foo(s: Inner) -> None:
    h(s.q)


@guppy(daggerable=True)
def test(s: Outer) -> None:
    foo(s.inner)


test.compile_function()
