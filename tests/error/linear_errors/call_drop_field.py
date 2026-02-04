from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q1: qubit
    q2: qubit


@guppy
def foo() -> MyStruct:
    return MyStruct(qubit(), qubit())


@guppy
def bar() -> qubit:
    return foo().q1


bar.compile()
