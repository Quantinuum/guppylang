from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


@guppy.struct
class MyStruct1:
    x: "MyStruct2"


@guppy.struct
class MyStruct2:
    q1: qubit
    q2: qubit


@guppy
def foo(s: MyStruct1 @owned) -> MyStruct1:
    measure(s.x.q1)
    return MyStruct1(s.x)


foo.compile()
