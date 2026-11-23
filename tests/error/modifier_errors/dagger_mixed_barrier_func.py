from guppylang.decorator import guppy
from guppylang.std.platform import barrier
from guppylang.std.quantum import qubit


@guppy.struct
class Mixed:
    q: qubit
    n: int


@guppy(daggerable=True)
def test(s: Mixed) -> None:
    barrier(s)


test.compile_function()
