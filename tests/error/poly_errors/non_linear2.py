from typing import Callable

from guppylang.decorator import guppy
from guppylang.std.quantum.functional import h
from guppylang.std.effects import effects

T = guppy.type_var("T")


# Pending https://github.com/Quantinuum/guppylang/issues/1760 we need to explicitly
# declare the effects of `x`
@guppy.declare
def foo(x: Callable[[T], T]) -> None: ...


@guppy
def main() -> None:
    foo(h)


main.compile()
