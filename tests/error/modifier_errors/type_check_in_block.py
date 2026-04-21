from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger:
        1 + True


test.compile()
