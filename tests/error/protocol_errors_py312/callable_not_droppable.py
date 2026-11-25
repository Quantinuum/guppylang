from collections.abc import Callable

from guppylang import guppy, qubit
from guppylang.std.lang import Drop, owned


@guppy.struct(frozen=True)
class Ignore:
    @guppy
    def __call__[T: Drop](self, x: T @ owned) -> int:
        return 0


@guppy
def apply(f: Callable[[qubit @ owned], int], q: qubit @ owned) -> int:
    return f(q)


@guppy
def main() -> int:
    return apply(Ignore(), qubit())


main.compile()
