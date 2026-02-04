from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(xs: list[int], q: qubit @owned) -> list[qubit]:
    return [q for x in xs]


foo.compile()
