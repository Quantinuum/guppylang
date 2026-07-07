from guppylang.decorator import guppy
from guppylang.std.builtins import Function


@guppy.comptime
def test(f: Function[[], int]) -> int:
    return f()


test.compile()
