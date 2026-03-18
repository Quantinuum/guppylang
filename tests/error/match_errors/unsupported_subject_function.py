from collections.abc import Callable

from tests.util import compile_guppy


@compile_guppy
def main(f: Callable[[int], int]) -> None:
    match f:
        case _:
            pass
