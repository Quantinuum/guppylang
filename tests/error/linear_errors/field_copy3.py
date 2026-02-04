from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q: qubit


@guppy
def foo(s: MyStruct @owned) -> tuple[qubit, MyStruct]:
    return s.q, s


foo.compile()
