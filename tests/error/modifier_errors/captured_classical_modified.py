from guppylang.decorator import guppy
from guppylang.std.builtins import power


@guppy
def test() -> int:
    x = 3
    with power(2):
        x += 1
    return x


test.compile()
