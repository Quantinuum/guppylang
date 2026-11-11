from guppylang.decorator import guppy
from guppylang.std.builtins import array, nat
from guppylang.std.quantum import qubit


@guppy
def helper(q: qubit) -> None:
    pass


@guppy.unitary
class foo:
    @guppy(controllable=True)
    def __call__(q: qubit) -> None:
        helper(q)

    @guppy
    def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
        pass


foo.compile()
