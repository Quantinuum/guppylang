from collections.abc import Callable

from guppylang import guppy


@guppy.struct(frozen=True)
class BadCallable:
    value: int


@guppy
def apply(f: Callable[[int], bool]) -> bool:
    return f(1)


@guppy
def main() -> bool:
    return apply(BadCallable(42))


main.compile()
