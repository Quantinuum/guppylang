from guppylang import guppy
from guppylang.std.quantum import qubit, h, measure 
from guppylang.std.lang import power


@guppy.comptime
def foo() -> None:
    q1 = qubit()
    with power(2):
        h(q1)
    measure(q1)
    

foo.compile()
