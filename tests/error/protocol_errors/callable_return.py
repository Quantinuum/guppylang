from collections.abc import Callable

from guppylang import guppy

@guppy
def bar(x: int) -> int:
    return x

@guppy
def main() -> Callable[[int], int]:
    return bar

main.compile_function()
