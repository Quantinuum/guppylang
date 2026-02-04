from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q: qubit
    x: int


@guppy
def foo(s: MyStruct @owned) -> int:
    return s.x


foo.compile()
