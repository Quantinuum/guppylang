#TODO: this test must work!

from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def foo(x: qubit) -> None: ...


@guppy.comptime(dagger=True)
def test(x: qubit) -> None:
    foo(x)


test.compile_function()
