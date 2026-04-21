from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger:
        a = 3


test.compile()
