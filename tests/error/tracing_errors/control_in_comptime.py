from guppylang import guppy
from guppylang.std.quantum import qubit, h, measure
from guppylang.std.lang import control


@guppy.comptime
def foo() -> None:
    q1 = qubit()
    q2 = qubit()
    with control(q2):
        h(q1)
    measure(q1)
    measure(q2) 


foo.compile()
