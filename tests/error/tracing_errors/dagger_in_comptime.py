from guppylang import guppy
from guppylang.std.quantum import qubit, h, measure
from guppylang.std.lang import dagger


@guppy.comptime
def foo() -> None:
    q1 = qubit()
    with dagger():
        h(q1)
    measure(q1)
    

foo.compile()
