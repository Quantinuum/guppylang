from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.effects import effects, ANY as ALL

@guppy.declare
def foo() -> Callable[[int], int] @ effects(ALL):
   ...

@guppy
def main() -> int:
    return foo()(5)

main.compile()