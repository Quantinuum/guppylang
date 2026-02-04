from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q: qubit


@guppy
def foo(b: bool) -> int:
    if b:
        s = MyStruct(qubit())
    else:
        s = MyStruct(qubit())
    return 42


foo.compile()
