from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.platform import barrier
from guppylang.std.quantum import qubit


@guppy
@no_type_check
def main() -> qubit:
    q = qubit()
    barrier(q, q)
    return q


main.compile()
