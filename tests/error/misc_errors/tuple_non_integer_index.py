from tests.util import compile_guppy

@compile_guppy
def foo(x: int) -> int:
    return (1, 2, 3)[1.2]
