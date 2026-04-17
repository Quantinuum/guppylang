from guppylang import guppy
from guppylang.std.lang import Copy


@guppy
def foo[T: (Copy, Bogus)](t: T) -> T:
    return t


@guppy
def main() -> None:
    foo(42)


main.compile()
