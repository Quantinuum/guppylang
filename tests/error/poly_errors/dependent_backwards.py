from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop


@guppy
def foo[x: T, T: (Copy, Drop)]() -> None:
    pass


@guppy
def main() -> None:
    foo[42, int]()


main.compile()
