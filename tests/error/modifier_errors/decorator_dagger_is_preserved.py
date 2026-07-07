from guppylang import guppy, qubit
from guppylang.std.builtins import dagger, Controllable


@guppy(daggerable=True)
def apply_unitary(f: Controllable[[qubit], None], q: qubit) -> None:
    with dagger:
        f(q)

@guppy.declare(controllable=True)
def foo(q: qubit) -> None:...

@guppy
def main(q1: qubit) -> None:
    apply_unitary(foo, q1)


main.check()