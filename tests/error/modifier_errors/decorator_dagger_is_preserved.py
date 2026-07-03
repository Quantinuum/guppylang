from guppylang import guppy, qubit
from guppylang.std.builtins import control, dagger, Controllable


@guppy(daggerable=True)
def apply_unitary(f: Controllable[[qubit], None], ctrl: qubit, q: qubit) -> None:
    with dagger:
        f(q)

@guppy.declare(controllable=True)
def foo(q: qubit) -> None:...

@guppy
def main(q1: qubit, q2: qubit) -> None:
    apply_unitary(foo, q1, q2)


main.check()