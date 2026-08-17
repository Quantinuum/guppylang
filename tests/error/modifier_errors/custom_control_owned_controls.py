from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    n = guppy.nat_var("n")

    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, controls: array[qubit, n] @ owned) -> None:
        pass


foo.compile()
