from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


@guppy.struct
class MyStruct1:
    q: qubit
    x: "MyStruct2"


@guppy.struct
class MyStruct2:
    q: qubit


@guppy
def foo(s: MyStruct1 @owned) -> MyStruct1:
    measure(s.q)
    s.q = s.x.q
    return s


foo.compile()
