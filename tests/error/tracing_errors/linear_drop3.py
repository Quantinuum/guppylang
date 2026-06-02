from guppylang.decorator import guppy
from guppylang.std.builtins import owned, array
from guppylang.std.quantum import qubit, measure


@guppy.comptime
def test(qs: array[qubit, 10] @ owned) -> None:
    for i in range(9):
        measure(qs[i])


test.compile()
