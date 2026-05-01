from guppylang.decorator import guppy
from guppylang.std.builtins import power, control, qubit


@guppy
def test(q: qubit) -> int:
    x = 1
    y = 10
    with control(q):  # noqa: SIM117
        with power(3):
            x += 1
            y -= 2
    return x + y


test.compile()
