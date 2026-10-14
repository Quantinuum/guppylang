from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy
def foo(xs: list[int] @owned, q: qubit @owned) -> list[qubit]:
    return [q for x in xs]


foo.compile()
