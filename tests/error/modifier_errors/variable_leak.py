from guppylang.decorator import guppy
from guppylang.std.builtins import power


# TODO: The error message is confusing.
@guppy
def test() -> int:
    with power(1):
        x = 1
    return x + 2


test.compile()
