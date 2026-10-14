from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.enum
class MyEnum:
    Var = {"q": qubit}


@guppy
def foo(xs: list[int] @owned) -> list[MyEnum]:
    e = MyEnum.Var(qubit())
    return [e for _ in xs]


foo.compile()
