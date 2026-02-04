from tests.util import compile_guppy


x = 42


@compile_guppy
def foo(x: int) -> int:
    return comptime(x + 1)
