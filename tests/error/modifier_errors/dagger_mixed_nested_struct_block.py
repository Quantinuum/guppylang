from guppylang.decorator import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import qubit, h


@guppy.struct
class Inner:
    q: qubit
    x: int


@guppy.struct
class Outer:
    inner: Inner
    q: qubit


@guppy(daggerable=True)
def foo(s: Outer) -> None:
    h(s.q)


@guppy
def test(s: Outer) -> None:
    with dagger:
        foo(s)


test.compile_function()
