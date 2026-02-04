from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(qs: list[tuple[qubit, bool]] @owned) -> list[qubit]:
    rs: list[qubit] = []
    for q, b in qs:
        rs += [q]
        if b:
            break
    return rs


foo.compile()
