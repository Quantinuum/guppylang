from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.enum
class MyEnum:
    Var1 = {"q1": qubit}


@guppy.declare
def bar(b: bool) -> bool:
    ...


@guppy
def foo(qe: list[MyEnum] @owned, b: bool) -> list[MyEnum]:
    return [e for e in qe if bar(b)]


foo.compile()
