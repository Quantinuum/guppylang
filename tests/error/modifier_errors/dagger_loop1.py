from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger:
        for _ in range(46):
            pass


test.compile()
