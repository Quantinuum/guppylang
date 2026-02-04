from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy
def foo(q: qubit @owned) -> None:
    while True:
        pass


foo.compile()
