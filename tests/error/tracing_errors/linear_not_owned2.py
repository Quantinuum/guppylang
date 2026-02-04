from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, measure


@guppy.comptime
def test(qs: array[qubit, 10]) -> None:
    measure(qs[0])


test.compile()
