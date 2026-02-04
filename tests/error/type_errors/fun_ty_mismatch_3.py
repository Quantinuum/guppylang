from collections.abc import Callable

from guppylang.decorator import guppy


@guppy
def foo(x: int) -> int:
    def bar(f: Callable[[int], bool]) -> bool:
        return f(42)

    return bar(foo)


foo.compile()
