from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import qubit


@guppy
def foo(q: qubit) -> None:
    result("foo", q)


foo.compile()
