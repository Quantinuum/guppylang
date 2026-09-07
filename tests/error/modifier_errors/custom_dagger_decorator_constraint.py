from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import measure, qubit


@guppy.unitary
class foo:
    @guppy(daggerable=True)
    def __call__(q: qubit @owned) -> None:
        measure(q)

    @guppy
    def daggered(q: qubit @owned) -> None:
        measure(q)


foo.compile()
