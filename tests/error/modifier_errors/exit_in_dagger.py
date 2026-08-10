from guppylang import guppy
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger():
        exit("a")

test.compile()
