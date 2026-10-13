from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.struct
class MyStruct:
    q: qubit


@guppy
def foo(xs: list[int] @owned, s: MyStruct @owned) -> list[qubit]:
    return [s.q for x in xs]


foo.compile()
