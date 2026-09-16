from guppylang import guppy, qubit
from guppylang.std.builtins import Unitary


@guppy.unitary
class dagger_only:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def daggered(q: qubit) -> None:
        pass


@guppy
def apply_unitary(f: Unitary[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test(q: qubit) -> None:
    apply_unitary(dagger_only, q)


test.compile_function()
