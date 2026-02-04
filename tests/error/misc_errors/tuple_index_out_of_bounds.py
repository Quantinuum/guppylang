from tests.util import compile_guppy

@compile_guppy
def foo() -> float:
    t = (1.0, 2.0)
    return t[10]
