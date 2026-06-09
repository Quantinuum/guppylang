from guppylang import guppy, qubit
from guppylang.std.builtins import Daggerable


@guppy
def no_flags(q: qubit) -> None:
    pass


@guppy
def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test(q: qubit) -> None:
    apply_dagger(no_flags, q)


test.compile_function()
