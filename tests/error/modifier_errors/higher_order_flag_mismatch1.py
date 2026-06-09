from guppylang import guppy, qubit
from guppylang.std.builtins import Controllable


@guppy(dagger=True)
def dagger_only(q: qubit) -> None:
    pass

@guppy
def apply_ctrl(f: Controllable[[qubit], None], q: qubit) -> None:
    f(q)

@guppy
def test(q: qubit) -> None:
    apply_ctrl(dagger_only, q)


test.compile_function()
