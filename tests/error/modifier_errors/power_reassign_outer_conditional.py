from guppylang import guppy
from guppylang.std.builtins import power


@guppy
def test(x: int, b: bool) -> None:
    with power(2):
        y = x + 1  # noqa: F841
        if b:
            x = 1


test.compile()
