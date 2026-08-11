from guppylang import guppy
from guppylang.std.builtins import Unitary, Function
from guppylang.std.quantum import qubit


@guppy(unitary=True)
def unitary(q: qubit) -> None:
    pass


@guppy
def apply_unitary(
    f: Unitary[[qubit], None], q: qubit
) -> None:
    f(q)


@guppy
def main(q: qubit) -> None:
    f: Function[[qubit], None] = unitary
    apply_unitary(f, q)


main.compile_function()
