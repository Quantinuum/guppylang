from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test(i: int) -> None:
    with dagger:
        while i < 46:
            pass

test.check()
