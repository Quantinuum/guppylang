from guppylang import qubit
from guppylang.decorator import guppy


@guppy(dagger=True)
def test() -> None:
    x = qubit()


test.compile()
