from guppylang import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger:
        x = 3


test.compile()
