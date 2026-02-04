from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q: qubit


@guppy
def foo(b: bool, s: MyStruct @owned) -> MyStruct:
    if b:
        s.q = qubit()
    else:
        s.q = qubit()
    s.q = qubit()
    return s


foo.compile()
