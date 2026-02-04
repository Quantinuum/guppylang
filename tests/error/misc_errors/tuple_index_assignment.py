from tests.util import compile_guppy

@compile_guppy
def foo() -> None:
    t = (1, 2, 3)
    t[1] = 4
