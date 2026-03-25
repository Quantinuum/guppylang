from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    for i in range(123):
        with dagger:
            continue


test.compile()
