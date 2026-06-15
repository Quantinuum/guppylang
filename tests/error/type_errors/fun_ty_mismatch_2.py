from guppylang.decorator import guppy
from guppylang.std.builtins import Fn


@guppy
def foo(x: int) -> int:
    def bar(f: Fn[[], int]) -> int:
        return f()

    return bar(foo)


foo.compile()
