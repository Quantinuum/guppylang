from guppylang import qubit
from guppylang import guppy
from guppylang.std.builtins import dagger

@guppy
def test() -> None:
    with dagger:
        x = qubit()


test.compile()
