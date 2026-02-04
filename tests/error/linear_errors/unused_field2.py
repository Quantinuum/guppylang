from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q1: qubit
    q2: qubit


@guppy
def foo(s: MyStruct @owned) -> qubit:
    return s.q1


foo.compile()
