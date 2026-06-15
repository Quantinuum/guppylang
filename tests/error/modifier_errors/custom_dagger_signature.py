from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def call_daggered(q: qubit, extra: qubit) -> None:
        pass


foo.compile()
