from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy(daggerable=True)
def test() -> None:
        if 2 > 46:
            pass


test.compile()
