from guppylang.decorator import guppy
from guppylang.std.builtins import dagger


@guppy
def test(b: bool) -> int:
    x = 3
    with dagger:
        x += 1
    if b:
        return x
    return 0


test.compile_function()
