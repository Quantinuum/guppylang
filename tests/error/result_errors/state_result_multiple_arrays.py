from typing import no_type_check
from guppylang.std.builtins import array
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit
from tests.util import compile_guppy

@compile_guppy
@no_type_check
def main(qs: array[qubit, 3], rs: array[qubit, 4]) -> None:
   state_result("foo", qs, rs)
