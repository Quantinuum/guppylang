from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(qs: list[qubit] @owned) -> list[int]:
    return [42 for q in qs]


foo.compile()
