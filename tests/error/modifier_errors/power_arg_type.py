from guppylang.decorator import guppy
from guppylang.std.builtins import power


@guppy
def test() -> None:
    with power(0.3):
        pass


test.compile()
