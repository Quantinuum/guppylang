from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.comptime
def test(q: qubit @ owned) -> None:
    pass


test.compile()
