from guppylang.std.builtins import Fn

from tests.util import compile_guppy


@compile_guppy
def foo() -> Fn[[int], int]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
