from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy(daggerable=True)
def test(q: qubit @ owned) -> qubit:
    q2, i = (q, 0)
    return q2


test.compile_function()
