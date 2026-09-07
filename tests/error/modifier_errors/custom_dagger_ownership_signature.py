from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def daggered(q: qubit @ owned) -> None:
        pass


foo.compile()
