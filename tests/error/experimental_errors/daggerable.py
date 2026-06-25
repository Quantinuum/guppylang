
from guppylang import guppy, qubit
from guppylang.std.builtins import Daggerable, Function
from guppylang.std.quantum import h


@guppy(unitary=True)
def unitary(q: qubit) -> None:
    pass


@guppy
def apply_control(f: Function[[qubit], None], q: qubit) -> Daggerable[[qubit], None]:
    f(q)
    return unitary


@guppy
def test(q: qubit) -> None:
    apply_control(h, q)


test.compile_function()
