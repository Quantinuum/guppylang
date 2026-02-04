from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.struct
class MyStruct:
    q1: qubit
    q2: qubit


@guppy
def foo(ss: list[MyStruct] @owned) -> list[qubit]:
    return [s.q1 for s in ss]


foo.compile()
