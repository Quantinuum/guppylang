from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy(dagger=True)
def test() -> None:
        x = 3 if 2 > 46 else 0


test.compile()
