from typing import no_type_check
from guppylang.std.builtins import array
from guppylang.std.debug import state_result
from tests.util import compile_guppy

@compile_guppy
def main(xs: array[int, 3]) -> None:
   state_result("foo", xs)
