from guppylang.decorator import guppy
from guppylang.std.builtins import array, nat
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled[n: nat](q: qubit, controls: array[int, n]) -> None:
        pass


foo.compile()
