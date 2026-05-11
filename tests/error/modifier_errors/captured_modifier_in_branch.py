from guppylang.decorator import guppy
from guppylang.std.builtins import power

@guppy
def test(b: bool) -> int:
    x = 0
    with power(2):
        if b:
            x = 3
    c = x +1
    return 0


test.check()
