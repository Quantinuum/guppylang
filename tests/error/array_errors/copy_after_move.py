from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> None:
   xs = array(1, 2, 3)
   ys = xs
   zs = xs.copy()


main.compile()
