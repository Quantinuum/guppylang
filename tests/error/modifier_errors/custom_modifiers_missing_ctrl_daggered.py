import guppylang
from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit

guppylang.enable_experimental_features()


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def daggered(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, _controls: array[qubit, 1]) -> None:
        pass
