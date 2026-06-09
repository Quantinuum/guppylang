from collections.abc import Callable
from guppylang import guppy, qubit


@guppy(dagger=True)
def dagger_only(q: qubit) -> None:
    pass

@guppy
def apply_power(f: Callable[[qubit], None], q: qubit) -> None:
    f(q)

@guppy
def test(q: qubit) -> None:
    apply_power(dagger_only, q)


test.compile_function()
