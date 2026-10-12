from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.quantum import measure, qubit


@guppy
def foo() -> None:
    pass

@guppy
def test() -> None:
    q = qubit()
    with dagger, control(q):
        foo()
    measure(q)

test.compile()
