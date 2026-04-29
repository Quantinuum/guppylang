from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.enum
class MyEnum:
    Var = {"q": qubit}


@guppy
def foo(xs: list[int], e: MyEnum @owned) -> list[MyEnum]:
    return [e for _ in xs]


foo.compile()
