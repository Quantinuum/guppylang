from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger:
        x = 1 if 2 > 46 else 0



test.compile()
