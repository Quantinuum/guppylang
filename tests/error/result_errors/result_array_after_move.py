from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.builtins import array, result


@guppy
@no_type_check
def main() -> None:
   xs = array(1, 2, 3)
   ys = xs
   result("foo", xs)


main.compile()
