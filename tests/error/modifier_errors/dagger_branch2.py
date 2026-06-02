from guppylang.decorator import guppy
from guppylang.std.builtins import dagger, power


@guppy
def test() -> None:
    with dagger, power(2):
        with dagger:
            ok = 3 if 2 > 46 else 0
        x = 1 if 2 > 46 else 0



test.compile()
