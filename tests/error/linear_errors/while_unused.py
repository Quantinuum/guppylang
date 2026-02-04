from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.quantum.functional import h


@guppy
def test(n: int) -> None:
    q = qubit()
    i = 0
    while i < n:
        q = h(q)
        i += 1


test.compile()
