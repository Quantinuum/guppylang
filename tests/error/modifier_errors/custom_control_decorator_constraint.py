from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy
def helper(q: qubit) -> None:
    pass


@guppy.unitary
class foo:
    n = guppy.nat_var("n")

    @guppy(controllable=True)
    def __call__(q: qubit) -> None:
        helper(q)

    @guppy
    def controlled(q: qubit, _controls: array[qubit, n]) -> None:
        pass


foo.compile()
