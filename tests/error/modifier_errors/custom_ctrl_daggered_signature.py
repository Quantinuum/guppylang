from guppylang.decorator import guppy
from guppylang.std.builtins import array, nat
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy(controllable=True)
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def ctrl_daggered[n: nat](q: int, controls: array[qubit, n]) -> None:
        pass


foo.compile()
