from tests.util import compile_guppy


@compile_guppy
def foo() -> None:
    i = 0
    while i < 3:
        i += 1
    else:
        print(i)
