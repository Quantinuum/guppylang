from typing import Callable

from guppylang.decorator import guppy
from guppylang.std.quantum import qubit

T = guppy.type_var("T")


@guppy.declare
def foo(x: Callable[[T], None]) -> None:
    ...

@guppy.declare
def h(q: qubit) -> None: ...


@guppy
def main() -> None:
    foo(h)


main.compile()
