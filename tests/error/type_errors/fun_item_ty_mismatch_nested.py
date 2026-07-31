from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    if x == 0:

        def bar(y: int) -> int:
            return y + 3
    else:

        def bar(y: int) -> int:
            return y - 42

    return bar(x)
