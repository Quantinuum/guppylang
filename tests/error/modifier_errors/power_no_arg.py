from guppylang.decorator import guppy
from guppylang.std.builtins import power


@guppy
def test() -> None:
    with power():
        pass


test.compile()
