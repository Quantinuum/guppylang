from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy
def test() -> None:
    with control(qubit()):
        pass


test.compile()
