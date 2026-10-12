from guppylang import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import qubit


@guppy
def foo() -> None:
    pass

@guppy
def test() -> None:
    with dagger:
        foo()

test.compile()
