from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy(controllable=True)
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def daggered(q: qubit) -> None:
        pass
