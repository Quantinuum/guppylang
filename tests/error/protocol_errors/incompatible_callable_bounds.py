from guppylang import guppy, qubit
from guppylang.std.builtins import Controllable, Daggerable


@guppy(unitary=True)
def apply[
    F: (
        Daggerable[[qubit], None],
        Controllable[[int], None],
    ),
](f: F, qs: qubit) -> None:
    return f(qs)


apply.check()
