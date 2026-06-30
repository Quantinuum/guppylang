from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.builtins import output
from guppylang.std.quantum import measure_array


@guppy
@no_type_check
def main() -> None:
    q = array(qubit(), qubit())
    m = measure_array(q)
    output("m", m)


main.compile()
