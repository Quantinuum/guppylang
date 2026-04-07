from guppylang import guppy, qubit
from guppylang.std.builtins import dagger


@guppy
def test() -> None:
    with dagger:
        p = qubit()


test.compile()
