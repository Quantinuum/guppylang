from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.struct
class MyStruct:
    q1: qubit
    q2: qubit


@guppy.declare
def bar(q: qubit @owned) -> bool:
    ...


@guppy
def foo(qs: list[MyStruct] @owned) -> list[qubit]:
    return [s.q2 for s in qs if bar(s.q1)]


foo.compile()
