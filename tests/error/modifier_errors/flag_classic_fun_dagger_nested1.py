from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.quantum import measure, qubit


@guppy
def foo() -> None:
    pass

@guppy(daggerable=True)
def test() -> None:
    foo()

test.compile()
