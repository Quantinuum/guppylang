from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.enum
class Enum:
    Var = {"q": qubit}

@guppy
def test(q: qubit) -> Enum:
    return Enum.Var(q)


test.compile()
