from tests.util import compile_guppy

@compile_guppy
def foo(b: bool) -> int:
    if b:
        return 2
    else:
        x = 1
        z = 2
        a = x + z
        result = a * 2
        temp = result - 1
        x = temp
        z = 2
        a = x + z
        result = a * 2
        temp = result - 1


foo.compile()