from guppylang.decorator import guppy
from guppylang.std.builtins import Function


@guppy
def foo(x: int) -> int:
    def bar(f: Function[[], int]) -> int:
        return f()

    return bar(foo)


foo.compile()
