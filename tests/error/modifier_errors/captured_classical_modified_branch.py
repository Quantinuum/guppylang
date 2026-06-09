from guppylang.decorator import guppy
from guppylang.std.builtins import power


@guppy
def test(b: bool) -> int:
    x = 3
    with power(2):
        x += 1
    if b:
        return x
    return 0


test.compile_function()
