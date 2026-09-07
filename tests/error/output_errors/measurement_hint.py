from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.builtins import output
from guppylang.std.quantum import measure


@guppy
@no_type_check
def main() -> None:
    q = qubit()
    m = measure(q)
    output("m", m)


main.compile()
