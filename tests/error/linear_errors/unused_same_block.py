from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy
def foo(q: qubit @owned) -> int:
    x = q
    x = 10
    return x


foo.compile()
