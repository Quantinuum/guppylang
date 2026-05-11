from collections.abc import Callable

from tests.util import compile_guppy

@compile_guppy
def foo() -> Callable[[nat], bool]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
