from typing import Callable

from guppylang.decorator import guppy
from guppylang.std.quantum.functional import h

T = guppy.type_var("T")


@guppy.declare
def foo(x: Callable[[T], T]) -> None: ...


@guppy
def main() -> None:
    foo(h)


main.compile()
