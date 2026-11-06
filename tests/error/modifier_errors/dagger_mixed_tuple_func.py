from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, h


@guppy(daggerable=True)
def foo(t: tuple[qubit, int]) -> None:
    h(t[0])


@guppy(daggerable=True)
def test(t: tuple[qubit, int]) -> None:
    foo(t)


test.compile_function()
