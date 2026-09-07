from guppylang.std.builtins import Function

from tests.util import compile_guppy


@compile_guppy
def foo() -> Function[[int], int]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
