from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def call_controlled(q: int, controls: array[qubit, 2]) -> None:
        pass


foo.compile()
