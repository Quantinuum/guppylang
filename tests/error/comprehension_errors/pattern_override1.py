from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(qs: list[tuple[qubit, qubit]] @owned) -> list[qubit]:
    return [q for q, q in qs]


foo.compile()
