from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.builtins import control


@guppy
def test() -> None:
    x = array(1, 2, 3)
    with control(x):
        pass


test.compile()
