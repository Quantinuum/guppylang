from guppylang import guppy, qubit
from guppylang.std.builtins import Daggerable, array


@guppy.unitary
class control_only:
    n = guppy.nat_var("n")

    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, _controls: array[qubit, n]) -> None:
        pass


@guppy
def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test(q: qubit) -> None:
    apply_dagger(control_only, q)


test.compile_function()
