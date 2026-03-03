from typing import Callable

from guppylang.decorator import guppy


T = guppy.type_var("T")


@guppy.declare
def generic_func(x: T) -> T: ...


@guppy.comptime
def main() -> Callable[[int], int]:
    return generic_func


main.compile()
