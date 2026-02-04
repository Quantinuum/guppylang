from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, cx


@guppy.comptime
def test(qs: array[qubit, 10]) -> None:
    cx(qs[0], qs[0])


test.compile()
