from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, h


@guppy
def foo(b: bool) -> None:
    q = qubit()
    if b:
        h(q)


foo.compile()
