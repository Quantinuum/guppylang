from guppylang.decorator import guppy
from guppylang.std.builtins import power

@guppy
def test(b: bool) -> int:
    x = 0 # error: if x defined here we do not get the error
    with power(2):
        if b:
            x = 3 # probably here is not visited?
    a = b
    c = x +1
    return 0


test.check()
