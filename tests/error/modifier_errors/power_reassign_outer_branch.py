from guppylang import guppy
from guppylang.std.builtins import power


@guppy
def test(b: bool) -> None:
    if b:  # noqa: SIM108
        x = 0
    else:
        x = 1
    with power(2):
        if b:
            x += 1


test.compile()
