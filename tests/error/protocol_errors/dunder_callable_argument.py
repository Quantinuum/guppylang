from collections.abc import Callable

from guppylang import guppy


@guppy.struct(frozen=True)
class BadCallable:
    @guppy
    def __call__(self, x: bool) -> bool:
        return x


@guppy
def apply(f: Callable[[int], bool]) -> bool:
    return f(1)


@guppy
def main() -> bool:
    return apply(BadCallable())


main.compile()
