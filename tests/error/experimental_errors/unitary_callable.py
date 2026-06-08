from guppylang import guppy, qubit
from guppylang.std.builtins import Controllable, Daggerable, Unitary
from guppylang.std.quantum import h


@guppy(unitary=True)
def unitary(q: qubit) -> None:
    pass


@guppy
def apply_control(f: Controllable[[qubit], None], q: qubit) -> Unitary[[qubit], None]:
    f(q)
    return unitary


@guppy
def test(q: qubit) -> None:
    apply_control(h, q)


test.compile_function()
