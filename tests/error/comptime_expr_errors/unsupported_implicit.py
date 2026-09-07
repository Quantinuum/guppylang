from tests.util import compile_guppy


s = {1, 2, 3}


@compile_guppy
def foo() -> int:
    return s
