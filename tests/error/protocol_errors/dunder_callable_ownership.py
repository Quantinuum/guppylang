from collections.abc import Callable

from guppylang import guppy, qubit
from guppylang.std.lang import owned
from guppylang.std.quantum import discard


@guppy.struct(frozen=True)
class Consume:
    @guppy
    def __call__(self, q: qubit @ owned) -> None:
        discard(q)


@guppy
def apply(f: Callable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def main() -> None:
    q = qubit()
    apply(Consume(), q)
    discard(q)


main.compile()
