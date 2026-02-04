from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(qs: list[qubit] @owned, xs: list[int]) -> list[qubit]:
    return [q for q in qs for x in xs]


foo.compile()
