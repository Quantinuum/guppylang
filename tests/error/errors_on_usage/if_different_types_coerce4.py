from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> float:
    y = 1 if x else 1.0
    return y
