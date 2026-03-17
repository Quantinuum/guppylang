from guppylang.std.builtins import array
from tests.util import compile_guppy


@compile_guppy
def main(a: array[int, 1]) -> None:
    match a:
        case _:
            pass
