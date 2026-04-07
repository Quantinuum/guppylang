from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


def test() -> None:
    with dagger:
        x = qubit()


test.compile()
