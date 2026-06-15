from guppylang.decorator import guppy
from guppylang.std.builtins import Fn


@guppy.comptime
def test(f: Fn[[], int]) -> int:
    return f()


test.compile()
