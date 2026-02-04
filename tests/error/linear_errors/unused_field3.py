from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


@guppy.struct
class MyStruct1:
    x: "MyStruct2"
    y: int


@guppy.struct
class MyStruct2:
    q1: qubit
    q2: qubit


@guppy
def foo(s: MyStruct1 @owned) -> int:
    measure(s.x.q1)
    return s.y


foo.compile()
