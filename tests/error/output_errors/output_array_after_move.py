from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.builtins import array, output


@guppy
@no_type_check
def main() -> None:
   xs = array(1, 2, 3)
   ys = xs
   output("foo", xs)


main.compile()
