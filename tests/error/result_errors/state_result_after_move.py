from typing import no_type_check
from guppylang.std.builtins import array, owned
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard_array
from tests.util import compile_guppy

@compile_guppy
@no_type_check
def main(qs: array[qubit, 3] @ owned) -> None:
   ys = qs
   state_result("foo", qs)
   discard_array(qs)
   discard_array(ys)
