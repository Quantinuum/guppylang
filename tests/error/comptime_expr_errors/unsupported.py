from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    return comptime({1, 2, 3})
