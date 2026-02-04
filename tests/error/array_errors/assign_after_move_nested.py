from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> None:
   xs = array(array(1, 2, 3), array(1, 2, 3))
   ys = xs
   xs[0][0] = 0


main.compile()
