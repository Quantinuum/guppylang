from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy(daggerable=True)
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, _controls: array[qubit, 1]) -> None:
        pass
