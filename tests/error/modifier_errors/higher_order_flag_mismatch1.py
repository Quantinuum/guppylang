from guppylang import guppy, qubit
from guppylang.std.builtins import Powerable


@guppy(dagger=True)
def dagger_only(q: qubit) -> None:
    pass


@guppy
def apply_power(f: Powerable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test(q: qubit) -> None:
    apply_power(dagger_only, q)


test.compile_function()
