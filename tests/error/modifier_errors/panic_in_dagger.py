from guppylang import guppy
from guppylang.std.builtins import dagger, panic


@guppy
def test() -> None:
    with dagger():
        panic("a")

test.compile()
