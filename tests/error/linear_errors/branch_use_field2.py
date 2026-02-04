from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


@guppy.struct
class MyStruct:
    q1: qubit
    q2: qubit


@guppy
def foo(b: bool, s: MyStruct @owned) -> MyStruct:
    if b:
        measure(s.q2)
    return s


foo.compile()
