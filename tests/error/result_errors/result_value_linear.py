from guppylang.decorator import guppy
from guppylang.std.builtins import output
from guppylang.std.quantum import qubit


@guppy
def foo(q: qubit) -> None:
    output("foo", q)


foo.compile()
