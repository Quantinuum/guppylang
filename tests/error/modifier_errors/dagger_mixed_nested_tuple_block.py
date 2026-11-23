from guppylang.decorator import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import h, qubit


@guppy(daggerable=True)
def foo(t: tuple[tuple[qubit, int], qubit]) -> None:
    h(t[1])


@guppy
def test(t: tuple[tuple[qubit, int], qubit]) -> None:
    with dagger:
        foo(t)


test.compile_function()
