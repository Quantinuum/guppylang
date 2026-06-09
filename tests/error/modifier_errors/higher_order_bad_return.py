from guppylang import guppy, qubit
from guppylang.std.builtins import Controllable, Unitary
from guppylang.std.quantum import h


@guppy(dagger=True)
def dagger_only(q: qubit) -> None:
    pass


@guppy
def apply_control(f: Controllable[[qubit], None], q: qubit) -> Unitary[[qubit], None]:
    f(q)
    return dagger_only


@guppy
def test(q: qubit) -> None:
    apply_control(h, q)


test.check()