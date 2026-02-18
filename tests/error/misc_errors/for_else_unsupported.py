from tests.util import compile_guppy


@compile_guppy
def foo() -> None:
    for i in range(3):
        pass
    else:
        print(i)
