from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit) -> None:
        pass


foo.compile()
