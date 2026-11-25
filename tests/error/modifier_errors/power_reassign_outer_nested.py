from guppylang import guppy
from guppylang.std.builtins import control, power, qubit


@guppy
def test(q: qubit, x: int) -> None:
    with power(2):  # noqa: SIM117
        with control(q):
            x += 1


test.compile()
