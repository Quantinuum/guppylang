from guppylang import guppy
from guppylang.std.builtins import power


@guppy
def test(x: int) -> None:
    with power(2):
        x = 1  # noqa: F841


test.compile()
