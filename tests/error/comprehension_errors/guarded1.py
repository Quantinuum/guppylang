from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(qs: list[tuple[bool, qubit]] @owned) -> list[qubit]:
    return [q for b, q in qs if b]


foo.compile()
