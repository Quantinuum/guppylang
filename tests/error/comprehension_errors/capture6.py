from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    Var = {"q": qubit}


@guppy
def foo(xs: list[int]) -> list[MyEnum]:
    e = MyEnum.Var(qubit())
    return [e for _ in xs]


foo.compile()
