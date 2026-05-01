from guppylang.decorator import guppy
from guppylang.std.builtins import power, control, qubit
from guppylang.std.num import nat


@guppy
def test(n: nat, q: qubit) -> int:
    x = 0
    with power(n):  # noqa: SIM117
        with control(q):
            x += 1
    return x


test.compile_function()
