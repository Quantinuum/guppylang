from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop


@guppy
def foo[T: (Copy, Drop), x: T]() -> None:
    pass


@guppy
def main() -> None:
    foo[int, 1.5]()


main.compile()
