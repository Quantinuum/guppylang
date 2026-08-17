from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> float:
    if x:
        y = 1
    else:
        y = 1.0
    return y
