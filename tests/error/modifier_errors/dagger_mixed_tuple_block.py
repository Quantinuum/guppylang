from guppylang.decorator import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import qubit, h


@guppy(daggerable=True)
def foo(t: tuple[qubit, int]) -> None:
    h(t[0])


@guppy
def test(t: tuple[qubit, int]) -> None:
    with dagger:
        foo(t)


test.compile_function()
