from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, controls: array[qubit, 1]) -> None:
        pass


foo.compile()
